"""Outgoing model calls never use user-supplied endpoints or log prompt content."""
import os
import httpx
from fastapi import HTTPException

OPENROUTER = "https://openrouter.ai/api/v1"
OLLAMA_DEFAULT = "http://127.0.0.1:11434"


class UpstreamFailure(Exception):
    def __init__(self, provider: str, status: int = 502, transient: bool = False):
        self.provider, self.status, self.transient = provider, status, transient
        super().__init__(f"{provider} returned {status}")


async def _post(url: str, body: dict, key: str | None = None, timeout: float = 90.0) -> dict:
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.post(url, json=body, headers=headers)
    except httpx.RequestError as exc:
        raise UpstreamFailure("provider", 502, transient=True) from exc
    if response.status_code != 200:
        raise UpstreamFailure("provider", response.status_code, transient=response.status_code in (429, 502, 503, 504))
    try:
        return response.json()
    except ValueError as exc:
        raise UpstreamFailure("provider") from exc


def local_url() -> str:
    # A deployment operator controls this setting, never an HTTP request or MCP tool.
    endpoint = os.getenv("OLLAMA_BASE_URL", OLLAMA_DEFAULT).rstrip("/")
    if not endpoint.startswith(("http://127.0.0.1:", "http://localhost:")):
        if os.getenv("GOREECLOUD_AI_ALLOW_REMOTE_OLLAMA") != "true":
            raise HTTPException(503, "Remote Ollama requires explicit operator authorization")
    return endpoint


async def chat(messages: list[dict], model: str, provider: str, allow_local_fallback: bool) -> dict:
    selected = provider
    if selected == "auto":
        selected = "openrouter" if os.getenv("OPENROUTER_API_KEY") else "ollama"
    if selected == "openrouter":
        key = os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise HTTPException(503, "OpenRouter API key missing")
        try:
            result = await _post(OPENROUTER + "/chat/completions", {
                "model": model if model != "local" else "openrouter/auto",
                "messages": messages, "max_tokens": 2048, "stream": False
            }, key)
            return {
                "provider": "openrouter", "model": result.get("model", model),
                "content": _extract_content(result), "usage": result.get("usage", {})
            }
        except UpstreamFailure as exc:
            if not (allow_local_fallback and exc.transient and os.getenv("OLLAMA_MODEL")):
                raise HTTPException(502, "OpenRouter request failed (see upstream service)") from exc
            selected = "ollama"
    if selected == "ollama":
        local_model = (model if provider == "ollama" and model not in ("local", "openrouter/auto") else os.getenv("OLLAMA_MODEL", ""))
        if not local_model:
            raise HTTPException(503, "Configure OLLAMA_MODEL for local inference")
        try:
            result = await _post(local_url() + "/api/chat", {
                "model": local_model, "messages": messages, "stream": False
            })
        except UpstreamFailure as exc:
            raise HTTPException(502, "Local model is unavailable") from exc
        return {
            "provider": "ollama", "model": result.get("model", local_model),
            "content": str((result.get("message") or {}).get("content") or ""),
            "usage": {}
        }
    raise HTTPException(422, "Unsupported provider")


def _extract_content(result: dict) -> str:
    choices = result.get("choices") or []
    if not choices:
        raise HTTPException(502, "Model returned no choices")
    value = (choices[0].get("message") or {}).get("content")
    if not isinstance(value, str):
        raise HTTPException(502, "Model returned non-text content")
    return value


async def image_request(prompt: str, model: str, reference: str | None) -> dict:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise HTTPException(503, "OpenRouter API key missing")
    body = {"model": model, "prompt": prompt}
    if reference:
        body["input_references"] = [{
            "type": "image_url", "image_url": {"url": reference}
        }]
    try:
        result = await _post(OPENROUTER + "/images", body, key, timeout=120)
    except UpstreamFailure as exc:
        raise HTTPException(502, "Image provider request failed") from exc
    data = result.get("data") or []
    if not data or not isinstance(data[0].get("b64_json"), str):
        raise HTTPException(502, "Image provider returned no image")
    media_type = data[0].get("media_type", "image/png")
    if media_type not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(502, "Unsupported generated image type")
    return {
        "model": model,
        "image": f"data:{media_type};base64,{data[0]['b64_json']}",
        "cost": (result.get("usage") or {}).get("cost")
    }
