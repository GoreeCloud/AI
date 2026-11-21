"""Outgoing model calls never use user-supplied endpoints or log prompt content."""
import asyncio
import base64
import binascii
import json
import math
import os
import re
from collections.abc import AsyncIterator
from urllib.parse import urlsplit

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
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:  # noqa: SIM117
            async with client.stream("POST", url, json=body, headers=headers) as response:
                if response.status_code != 200:
                    raise UpstreamFailure("provider", response.status_code,
                                          transient=response.status_code in (429, 502, 503, 504))
                limit = 24_000_000
                raw = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=65536):
                    if len(raw) + len(chunk) > limit:
                        raise UpstreamFailure("provider", 413)
                    raw.extend(chunk)
    except httpx.RequestError as exc:
        raise UpstreamFailure("provider", 502, transient=True) from exc
    try:
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError("Upstream JSON must be an object")
        return result
    except (ValueError, UnicodeError) as exc:
        raise UpstreamFailure("provider") from exc


def local_url() -> str:
    # A deployment operator controls this setting, never an HTTP request or MCP tool.
    endpoint = os.getenv("OLLAMA_BASE_URL", OLLAMA_DEFAULT).rstrip("/")
    parsed = urlsplit(endpoint)
    try:
        valid_port = parsed.port is not None and 1 <= parsed.port <= 65535
    except ValueError:
        valid_port = False
    if (not valid_port or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path not in ("", "/")):
        raise HTTPException(503, "Invalid Ollama endpoint configuration")
    local = parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost")
    remote = (parsed.scheme == "https" and
              os.getenv("GOREECLOUD_AI_ALLOW_REMOTE_OLLAMA") == "true")
    if not (local or remote):
        raise HTTPException(503, "Ollama requires loopback or approved remote HTTPS")
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
                "content": _extract_content(result), "usage": result.get("usage", {}),
                **({"generation_id": validated_generation_id(result.get("id"))}
                   if validated_generation_id(result.get("id")) else {})
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
    data = result.get("data")
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        raise HTTPException(502, "Image provider returned no image")
    encoded = data[0].get("b64_json")
    media_type = data[0].get("media_type", "image/png")
    if not isinstance(encoded, str) or not 0 < len(encoded) <= 18_000_000:
        raise HTTPException(502, "Image provider returned invalid image bytes")
    if media_type not in ("image/png", "image/jpeg", "image/webp"):
        raise HTTPException(502, "Unsupported generated image type")
    try:
        binary = base64.b64decode(encoded, validate=True)
    except binascii.Error as exc:
        raise HTTPException(502, "Image provider returned invalid image encoding") from exc
    signatures = {
        "image/png": binary.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/jpeg": binary.startswith(b"\xff\xd8\xff"),
        "image/webp": binary.startswith(b"RIFF") and binary[8:12] == b"WEBP"
    }
    if len(binary) > 12_000_000 or not signatures[media_type]:
        raise HTTPException(502, "Image provider returned invalid image format")
    usage = result.get("usage") or {}
    cost = usage.get("cost") if isinstance(usage, dict) else None
    if cost is not None and (type(cost) not in (int, float) or not math.isfinite(cost) or cost < 0):
        cost = None
    return {
        "model": model, "image": f"data:{media_type};base64,{encoded}", "cost": cost,
        "media_type": media_type,
        **({"generation_id": validated_generation_id(result.get("id"))}
           if validated_generation_id(result.get("id")) else {})
    }


async def stream_chat(messages: list[dict], model: str, provider: str) -> AsyncIterator[dict]:
    """Stream bounded structured events; caller authenticates and authorizes cloud access.

    This request does not retry or switch providers mid-stream. Cancellation of the
    consuming request closes the upstream connection and stops further generation.
    """
    if provider == "openrouter":
        key = os.getenv("OPENROUTER_API_KEY")
        if not key:
            yield {"type": "error", "message": "Cloud model is not configured"}
            return
        url = OPENROUTER + "/chat/completions"
        body = {"model": model if model != "local" else "openrouter/auto",
                "messages": messages, "max_tokens": 2048, "stream": True}
        headers = {"Authorization": "Bearer " + key}
    elif provider == "ollama":
        selected = model if model not in ("openrouter/auto", "local") else os.getenv("OLLAMA_MODEL", "")
        if not selected:
            yield {"type": "error", "message": "Local model is not configured"}
            return
        url = local_url() + "/api/chat"
        body = {"model": selected, "messages": messages, "stream": True}
        headers = {}
    else:
        yield {"type": "error", "message": "Invalid selected provider"}
        return

    produced = 0
    final_model = body["model"]
    generation_id = None
    try:
        async with httpx.AsyncClient(timeout=90, follow_redirects=False, trust_env=False) as client:  # noqa: SIM117
            async with client.stream("POST", url, json=body, headers=headers) as response:
                if response.status_code != 200:
                    yield {"type": "error", "message": "Inference provider returned an error"}
                    return
                if provider == "openrouter":
                    generation_id = validated_generation_id(
                        getattr(response, "headers", {}).get("X-Generation-Id")
                    )
                async for line in response.aiter_lines():
                    if len(line) > 100_000:
                        yield {"type": "error", "message": "Upstream response exceeded limit"}
                        return
                    if provider == "openrouter":
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            break
                    else:
                        data = line
                    if not data:
                        continue
                    try:
                        event = json.loads(data)
                    except (ValueError, TypeError):
                        continue
                    if isinstance(event, dict) and event.get("error"):
                        yield {"type": "error", "message": "Inference provider reported an error"}
                        return
                    if not isinstance(event, dict):
                        continue
                    if provider == "openrouter":
                        generation_id = validated_generation_id(event.get("id")) or generation_id
                    final_model = str(event.get("model") or final_model)[:128]
                    if provider == "openrouter":
                        choices = event.get("choices") or []
                        delta = (choices[0].get("delta") or {}).get("content") if choices else None
                    else:
                        delta = (event.get("message") or {}).get("content")
                    if isinstance(delta, str) and delta:
                        produced += len(delta)
                        if produced > 120_000:
                            yield {"type": "error", "message": "Response text limit reached"}
                            return
                        yield {"type": "delta", "content": delta}
                    if provider == "ollama" and event.get("done") is True:
                        break
    except httpx.RequestError:
        yield {"type": "error", "message": "Inference provider is unreachable"}
        return
    done = {"type": "done", "provider": provider, "model": final_model}
    if provider == "openrouter" and generation_id:
        done["generation_id"] = generation_id
    yield done


async def verify_cloud_key_budget() -> None:
    """Optional fail-closed check of OpenRouter's provider-owned per-key limit.

    This does not reserve dollars or guarantee a maximum cost per in-flight call;
    the provider-side cap is the enforcement boundary. No user content is sent.
    """
    mode = os.getenv("GOREECLOUD_AI_REQUIRE_CAPPED_OPENROUTER_KEY", "false").lower()
    if mode not in ("true", "false"):
        raise HTTPException(503, "Invalid cloud budget policy")
    if mode == "false":
        return
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise HTTPException(503, "OpenRouter key is not configured")
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=False, trust_env=False) as client:
            response = await client.get(OPENROUTER + "/key", headers={
                "Authorization": "Bearer " + key
            })
        if response.status_code != 200 or len(response.content) > 65536:
            raise ValueError("budget lookup unavailable")
        info = response.json().get("data", {})
        limit = info.get("limit")
        remaining = info.get("limit_remaining")
        if (type(limit) not in (int, float) or type(remaining) not in (int, float)
                or not 0 < limit < 1_000_000_000 or not 0 < remaining <= limit):
            raise ValueError("no available capped provider balance")
        # BYOK requests can bypass per-key credits unless opted into the cap.
        if info.get("include_byok_in_limit") is not True:
            raise ValueError("BYOK use could bypass this key cap")
    except (httpx.RequestError, ValueError, TypeError, AttributeError) as exc:
        raise HTTPException(503, "Provider key cap could not be verified") from exc



async def image_catalog() -> dict:
    """Get provider-public model metadata via server-only authenticated GET.

    No prompt or paid generation request is sent. Provider credentials remain
    on the server; clients receive bounded, validated capability metadata.
    """
    url = OPENROUTER + "/images/models"
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "OpenRouter API key is not configured")
    try:
        async with httpx.AsyncClient(timeout=12, follow_redirects=False, trust_env=False) as client:  # noqa: SIM117
            async with client.stream("GET", url, headers={
                "Authorization": "Bearer " + key, "Accept": "application/json"
            }) as response:
                if response.status_code != 200:
                    raise ValueError("catalog source unavailable")
                raw = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=32768):
                    if len(raw) + len(chunk) > 3_000_000:
                        raise ValueError("catalog response exceeded limit")
                    raw.extend(chunk)
        payload = json.loads(raw)
        models = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(models, list) or len(models) > 1000:
            raise ValueError("invalid catalog shape")
        entries = []
        for model in models:
            if not isinstance(model, dict):
                continue
            slug = model.get("id")
            if not isinstance(slug, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._:/-]{1,127}", slug):
                continue
            params = model.get("supported_parameters")
            if not isinstance(params, dict):
                params = {}
            title = model.get("name")
            if not isinstance(title, str) or not title.strip():
                title = slug
            entries.append({
                "id": slug,
                "name": title.strip()[:120],
                "supports_reference": "input_references" in params,
                "supports_streaming": model.get("supports_streaming") is True,
            })
        if not entries:
            raise ValueError("no valid image catalog models")
        entries.sort(key=lambda x: x["name"].lower())
        return {"models": entries[:200], "source": "openrouter-image-api",
                "note": "Preview catalog; a model may change availability or price without notice."}
    except (httpx.RequestError, ValueError, TypeError, UnicodeError) as exc:
        raise HTTPException(503, "Image model catalog unavailable") from exc



# OpenRouter documents a gen-* ID, maximum length 128. The ID is metadata,
# not a bearer credential or permission to view someone else's generations.
_GENERATION_PATTERN = re.compile(r"gen-[A-Za-z0-9-]{1,124}")
_generation_slots = asyncio.Semaphore(2)


def validated_generation_id(value) -> str | None:
    if isinstance(value, str) and _GENERATION_PATTERN.fullmatch(value):
        return value
    return None


async def generation_cost(generation_id: str) -> dict:
    """Deliberately requested OpenRouter *metadata* lookup, no model request.

    Provider-reported cost is not an independent invoice or hard budget gate.
    Prompts, completions, full provider metadata and bearer key are discarded.
    """
    if validated_generation_id(generation_id) != generation_id:
        raise HTTPException(422, "Invalid OpenRouter generation ID")
    key = os.getenv("OPENROUTER_API_KEY", "")
    if not key:
        raise HTTPException(503, "OpenRouter API key is not configured")
    try:
        await asyncio.wait_for(_generation_slots.acquire(), timeout=0.5)
    except TimeoutError as exc:
        raise HTTPException(429, "Provider accounting capacity is busy") from exc
    try:
        try:
            async with (
                httpx.AsyncClient(timeout=8, follow_redirects=False, trust_env=False) as client,
                client.stream("GET", OPENROUTER + "/generation",
                              params={"id": generation_id},
                              headers={"Authorization": "Bearer " + key,
                                       "Accept": "application/json"}) as response,
            ):
                    if response.status_code != 200:
                        raise HTTPException(502, "Provider generation metadata is unavailable")
                    buffer = bytearray()
                    async for part in response.aiter_bytes():
                        if len(buffer) + len(part) > 65536:
                            raise HTTPException(502, "Provider generation metadata exceeded limit")
                        buffer.extend(part)
        except httpx.RequestError as exc:
            raise HTTPException(502, "Provider generation metadata is unreachable") from exc
        try:
            payload = json.loads(buffer)
            info = payload.get("data") if isinstance(payload, dict) else None
            if not isinstance(info, dict) or info.get("id") != generation_id:
                raise ValueError("Invalid generation metadata")
            amount = info.get("total_cost")
            if (type(amount) not in (int, float) or not math.isfinite(amount)
                    or not 0 <= amount <= 1_000_000):
                raise ValueError("Invalid provider-reported cost")
            model = info.get("model")
            if not isinstance(model, str) or not 1 <= len(model) <= 128:
                raise ValueError("Invalid reported model")
        except (TypeError, ValueError) as exc:
            raise HTTPException(502, "Provider generation metadata could not be validated") from exc
        return {
            "generation_id": generation_id,
            "model": model,
            "total_cost_usd": amount,
            "source": "openrouter-reported-generation",
            "note": "Provider metadata only; not an independent invoice or hard USD spending cap",
        }
    finally:
        _generation_slots.release()
