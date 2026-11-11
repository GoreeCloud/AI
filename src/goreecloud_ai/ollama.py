"""Small async adapter for the official Ollama REST API."""
import httpx


class OllamaError(Exception):
    """Unavailable or invalid upstream response."""


class OllamaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(8.0)) as client:
                response = await client.get(self.base_url + "/api/tags")
                response.raise_for_status()
                data = response.json()
                return [m["name"] for m in data.get("models", []) if isinstance(m, dict) and isinstance(m.get("name"), str)]
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise OllamaError("Unable to list installed Ollama models") from exc

    async def chat(self, model: str, messages: list[dict[str, str]]) -> str:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=180, write=10, pool=10)) as client:
                response = await client.post(
                    self.base_url + "/api/chat",
                    json={"model": model, "messages": messages, "stream": False},
                )
                response.raise_for_status()
                content = response.json().get("message", {}).get("content")
                if not isinstance(content, str):
                    raise OllamaError("Ollama returned a malformed chat response")
                return content
        except (httpx.HTTPError, ValueError, TypeError) as exc:
            raise OllamaError("Ollama chat request failed") from exc


    async def stream_chat(self, model: str, messages: list[dict[str, str]]):
        """Yield complete text fragments from Ollama's NDJSON stream."""
        import json
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=180, write=10, pool=10)) as client:
                async with client.stream(
                    "POST", self.base_url + "/api/chat",
                    json={"model": model, "messages": messages, "stream": True},
                ) as response:
                    response.raise_for_status()
                    completed = False
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                        except (ValueError, TypeError) as exc:
                            raise OllamaError("Malformed Ollama stream event") from exc
                        if event.get("error"):
                            raise OllamaError("Ollama stream failed")
                        text = event.get("message", {}).get("content", "")
                        if not isinstance(text, str):
                            raise OllamaError("Invalid text fragment from Ollama")
                        if text:
                            yield text
                        if event.get("done"):
                            completed = True
                            break
                    if not completed:
                        raise OllamaError("Ollama stream ended before completion")
        except httpx.HTTPError as exc:
            raise OllamaError("Ollama stream request failed") from exc
