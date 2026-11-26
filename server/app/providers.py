"""Outgoing model calls never use user-supplied endpoints or log prompt content."""
import asyncio
import base64
import binascii
import io
import json
import math
import os
import re
from collections.abc import AsyncIterator
from contextlib import aclosing
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException

OPENROUTER = "https://openrouter.ai/api/v1"
OLLAMA_DEFAULT = "http://127.0.0.1:11434"
_STREAM_LINE_CHAR_LIMIT = 100_000
_STREAM_LINE_END = re.compile(r"\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]")


class UpstreamFailure(Exception):
    def __init__(self, provider: str, status: int = 502, transient: bool = False):
        self.provider, self.status, self.transient = provider, status, transient
        super().__init__(f"{provider} returned {status}")


async def _post(url: str, body: dict, key: str | None = None, timeout: float = 90.0,
                cache_headers: dict[str, str] | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = "Bearer " + key
    if cache_headers:
        headers.update(cache_headers)
    cache_status = None
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:  # noqa: SIM117
            async with client.stream("POST", url, json=body, headers=headers) as response:
                if response.status_code != 200:
                    raise UpstreamFailure("provider", response.status_code,
                                          transient=response.status_code in (429, 502, 503, 504))
                if cache_headers:
                    marker = response.headers.get("X-OpenRouter-Cache-Status", "").upper()
                    cache_status = marker if marker in ("HIT", "MISS") else None
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
        if cache_headers:
            result["_goreecloud_cache_status"] = cache_status
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


def _provider_cache_headers(enabled: bool) -> dict[str, str]:
    # OpenRouter's opt-in response cache is provider-side retention, not local
    # RAM caching, and does not change GoreeCloud's HTTP no-store response.
    return {"X-OpenRouter-Cache": "true", "X-OpenRouter-Cache-TTL": "300"} if enabled else {}


def _cache_token_report(usage: dict) -> dict:
    if not isinstance(usage, dict):
        return {}
    details = usage.get("prompt_tokens_details")
    if not isinstance(details, dict):
        return {}
    values = {}
    for name in ("cached_tokens", "cache_write_tokens"):
        value = details.get(name)
        if type(value) is int and 0 <= value <= 100_000_000:
            values[name] = value
    return values


async def chat(messages: list[dict], model: str, provider: str,
               allow_local_fallback: bool, provider_response_cache: bool = False,
               provider_prompt_cache: bool = False,
               cache_session_id: str | None = None,
               max_output_tokens: int = 2048) -> dict:
    selected = provider
    if selected == "auto":
        selected = "openrouter" if os.getenv("OPENROUTER_API_KEY") else "ollama"
    if selected == "openrouter":
        key = os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise HTTPException(503, "OpenRouter API key missing")
        try:
            body = {
                "model": model if model != "local" else "openrouter/auto",
                "messages": messages, "max_tokens": max_output_tokens, "stream": False
            }
            if provider_prompt_cache:
                body["cache_control"] = {"type": "ephemeral"}
                if cache_session_id:
                    body["session_id"] = cache_session_id
            if provider_response_cache:
                result = await _post(
                    OPENROUTER + "/chat/completions", body, key,
                    cache_headers=_provider_cache_headers(True),
                )
            else:
                result = await _post(OPENROUTER + "/chat/completions", body, key)
            usage = result.get("usage", {})
            report = {
                "provider": "openrouter", "model": result.get("model", model),
                "content": _extract_content(result), "usage": usage,
                **({"generation_id": validated_generation_id(result.get("id"))}
                   if validated_generation_id(result.get("id")) else {})
            }
            if provider_response_cache:
                marker = result.get("_goreecloud_cache_status")
                report["provider_response_cache"] = {
                    "requested": True,
                    "status": marker if marker in ("HIT", "MISS") else "UNKNOWN",
                }
            if provider_prompt_cache:
                report["provider_prompt_cache"] = {
                    "requested": True,
                    "reported_token_details": _cache_token_report(usage),
                }
            if provider_response_cache and report["provider_response_cache"]["status"] == "HIT":
                # Cached provider bodies may replay prior usage and generation IDs.
                # Never misattribute a previous paid generation to a new cache read.
                report["usage"] = {}
                report.pop("generation_id", None)
                if provider_prompt_cache:
                    report["provider_prompt_cache"]["reported_token_details"] = {}
            return report
        except UpstreamFailure as exc:
            if not (allow_local_fallback and exc.transient and os.getenv("OLLAMA_MODEL")):
                raise HTTPException(502, "OpenRouter request failed (see upstream service)") from exc
            selected = "ollama"
    if selected == "ollama":
        local_model = (model if provider == "ollama" and model not in ("local", "openrouter/auto") else os.getenv("OLLAMA_MODEL", ""))
        if not local_model:
            raise HTTPException(503, "Configure OLLAMA_MODEL for local inference")
        try:
            payload = {"model": local_model, "messages": messages, "stream": False}
            if max_output_tokens != 2048:
                payload["options"] = {"num_predict": max_output_tokens}
            result = await _post(local_url() + "/api/chat", payload)
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


def _stream_delta(event: dict, provider: str) -> str | None:
    if provider == "openrouter":
        choices = event.get("choices")
        if choices is not None and (not isinstance(choices, list)
                                    or (choices and not isinstance(choices[0], dict))):
            raise ValueError("Invalid stream choices")
        message = choices[0].get("delta") if choices else None
    else:
        if event.get("done") is not None and not isinstance(event["done"], bool):
            raise ValueError("Invalid stream completion flag")
        message = event.get("message")
    # Metadata and completion frames can omit message text.
    if message is None:
        return None
    if not isinstance(message, dict):
        raise ValueError("Invalid stream message")
    text = message.get("content")
    if text is not None and not isinstance(text, str):
        raise ValueError("Invalid stream text")
    return text


class _UpstreamLineLimitExceeded(Exception):
    pass


async def _bounded_stream_lines(response: httpx.Response) -> AsyncIterator[str]:
    pending = io.StringIO()
    trailing_cr = False
    async with aclosing(response.aiter_text()) as chunks:
        async for text in chunks:
            # Let HTTPX decode incrementally and preserve its splitlines semantics,
            # including CRLF split between chunks. The cap measures decoded characters.
            if trailing_cr:
                text = "\r" + text
            trailing_cr = text.endswith("\r")
            if trailing_cr:
                text = text[:-1]

            start = 0
            for end in _STREAM_LINE_END.finditer(text):
                if pending.tell() + end.start() - start > _STREAM_LINE_CHAR_LIMIT:
                    raise _UpstreamLineLimitExceeded
                pending.write(text[start:end.start()])
                yield pending.getvalue()
                pending.seek(0)
                pending.truncate()
                start = end.end()

            if pending.tell() + len(text) - start > _STREAM_LINE_CHAR_LIMIT:
                raise _UpstreamLineLimitExceeded
            pending.write(text[start:])
        if pending.tell() or trailing_cr:
            yield pending.getvalue()


async def stream_chat(messages: list[dict], model: str, provider: str,
                      provider_response_cache: bool = False,
                      provider_prompt_cache: bool = False,
                      cache_session_id: str | None = None,
                      max_output_tokens: int = 2048,
                      expose_terminal: bool = False) -> AsyncIterator[dict]:
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
                "messages": messages, "max_tokens": max_output_tokens, "stream": True}
        if provider_prompt_cache:
            body["cache_control"] = {"type": "ephemeral"}
            if cache_session_id:
                body["session_id"] = cache_session_id
        headers = {"Authorization": "Bearer " + key,
                   **_provider_cache_headers(provider_response_cache)}
    elif provider == "ollama":
        selected = model if model not in ("openrouter/auto", "local") else os.getenv("OLLAMA_MODEL", "")
        if not selected:
            yield {"type": "error", "message": "Local model is not configured"}
            return
        url = local_url() + "/api/chat"
        body = {"model": selected, "messages": messages, "stream": True}
        if max_output_tokens != 2048:
            body["options"] = {"num_predict": max_output_tokens}
        headers = {}
    else:
        yield {"type": "error", "message": "Invalid selected provider"}
        return

    produced = 0
    upstream_terminal = False
    final_model = body["model"][:128]
    generation_id = None
    cache_status = None
    usage_tokens = {}
    try:
        async with httpx.AsyncClient(timeout=90, follow_redirects=False, trust_env=False) as client:  # noqa: SIM117
            async with (
                client.stream("POST", url, json=body, headers=headers) as response,
                aclosing(_bounded_stream_lines(response)) as lines,
            ):
                if response.status_code != 200:
                    yield {"type": "error", "message": "Inference provider returned an error"}
                    return
                if provider == "openrouter":
                    generation_id = validated_generation_id(
                        getattr(response, "headers", {}).get("X-Generation-Id")
                    )
                    if provider_response_cache:
                        marker = response.headers.get("X-OpenRouter-Cache-Status", "").upper()
                        cache_status = marker if marker in ("HIT", "MISS") else "UNKNOWN"
                async for line in lines:
                    if provider == "openrouter":
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].removeprefix(" ")
                        if data == "[DONE]":
                            upstream_terminal = True
                            break
                    else:
                        data = line
                    if not data.strip():
                        continue
                    try:
                        event = json.loads(data)
                        if not isinstance(event, dict):
                            raise ValueError("Invalid stream event")
                        provider_failed = bool(event.get("error"))
                        delta = None if provider_failed else _stream_delta(event, provider)
                    except (ValueError, RecursionError):
                        yield {"type": "error", "message": "Inference provider returned invalid stream data"}
                        return
                    if provider_failed:
                        yield {"type": "error", "message": "Inference provider reported an error"}
                        return
                    if provider == "openrouter":
                        generation_id = validated_generation_id(event.get("id")) or generation_id
                        if provider_prompt_cache:
                            usage_tokens = _cache_token_report(event.get("usage", {})) or usage_tokens
                    streamed_model = event.get("model")
                    if isinstance(streamed_model, str) and streamed_model:
                        final_model = streamed_model[:128]
                    if delta:
                        produced += len(delta)
                        if produced > 120_000:
                            yield {"type": "error", "message": "Response text limit reached"}
                            return
                        yield {"type": "delta", "content": delta}
                    if provider == "ollama" and event.get("done") is True:
                        upstream_terminal = True
                        break
    except _UpstreamLineLimitExceeded:
        yield {"type": "error", "message": "Upstream response exceeded limit"}
        return
    except httpx.RequestError:
        yield {"type": "error", "message": "Inference provider is unreachable"}
        return
    if not upstream_terminal:
        yield {"type": "error", "message": "Model stream stopped before completion"}
        return
    done = {"type": "done", "provider": provider, "model": final_model}
    if expose_terminal:
        # Preserve the confirmation used by opt-in response-cache admission.
        done["upstream_terminal"] = upstream_terminal
    if provider == "openrouter" and generation_id and cache_status != "HIT":
        done["generation_id"] = generation_id
    if provider == "openrouter" and provider_response_cache:
        done["provider_response_cache"] = {"requested": True, "status": cache_status}
    if provider == "openrouter" and provider_prompt_cache:
        done["provider_prompt_cache"] = {
            "requested": True,
            "reported_token_details": {} if cache_status == "HIT" else usage_tokens,
        }
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




# Read-only provider capability discovery. No prompt or user-selected search
# query is ever sent upstream; the browser filters the sanitized catalog locally.
_text_catalog_slots = asyncio.Semaphore(2)


async def text_model_catalog() -> dict:
    """Deliberate owner request for bounded OpenRouter text-model metadata.

    This is discovery only: no inference, paid tokens, model validation guarantee
    or cloud-processing consent grant. Credentials are retained server-side.
    """
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise HTTPException(503, "OpenRouter API key is not configured")
    try:
        await asyncio.wait_for(_text_catalog_slots.acquire(), timeout=0.5)
    except TimeoutError as exc:
        raise HTTPException(429, "Model catalog capacity is busy") from exc
    try:
        try:
            async with httpx.AsyncClient(timeout=12, follow_redirects=False,
                                         trust_env=False) as client, client.stream(
                "GET", OPENROUTER + "/models",
                params={"output_modalities": "text"},
                headers={"Authorization": "Bearer " + key,
                         "Accept": "application/json"},
            ) as response:
                if response.status_code != 200:
                    raise ValueError("model catalog unavailable")
                buffer = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=32768):
                    if len(buffer) + len(chunk) > 8_000_000:
                        raise ValueError("model catalog exceeded memory bound")
                    buffer.extend(chunk)
            raw = json.loads(buffer)
            data = raw.get("data") if isinstance(raw, dict) else None
            if not isinstance(data, list) or not 1 <= len(data) <= 2500:
                raise ValueError("invalid model catalog")
            entries = []
            seen = set()
            for item in data:
                if not isinstance(item, dict):
                    continue
                slug = item.get("id")
                if (not isinstance(slug, str)
                        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{1,127}", slug)
                        or slug in seen):
                    continue
                seen.add(slug)
                name = item.get("name")
                if not isinstance(name, str) or not name.strip():
                    name = slug
                context = item.get("context_length")
                if type(context) is not int or not 1 <= context <= 50_000_000:
                    context = None
                parameters = item.get("supported_parameters")
                if not isinstance(parameters, list):
                    parameters = []
                entries.append({
                    "id": slug,
                    "name": name.strip()[:120],
                    "context_length": context,
                    "supports_tools": "tools" in parameters or "tool_choice" in parameters,
                })
            if not entries:
                raise ValueError("no valid text model metadata")
            entries.sort(key=lambda item: (item["name"].casefold(), item["id"]))
            return {
                "models": entries[:250],
                "truncated": len(entries) > 250,
                "source": "openrouter-text-model-catalog",
                "note": "Provider metadata can change without notice; discovery is not a paid call or price quote.",
            }
        except (httpx.RequestError, ValueError, TypeError, UnicodeError) as exc:
            raise HTTPException(503, "Text model catalog unavailable") from exc
    finally:
        _text_catalog_slots.release()


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
