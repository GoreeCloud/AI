"""No paid calls: mock OpenRouter response and prompt caching requests."""
import json

import httpx
import pytest
from fastapi import HTTPException

from app import providers

MESSAGES = [{"role": "user", "content": "synthetic question for cache tests"}]


def patch_transport(monkeypatch, handler):
    original = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: original(transport=transport, **kwargs))


@pytest.mark.asyncio
async def test_openrouter_response_and_anthropic_prompt_cache_metadata(monkeypatch):
    captured = []
    def handler(request):
        payload = json.loads(request.content)
        captured.append((dict(request.headers), payload, str(request.url)))
        return httpx.Response(
            200, headers={"X-OpenRouter-Cache-Status": "HIT"},
            json={"model": "anthropic/claude-test", "id": "gen-123AB",
                  "choices": [{"message": {"content": "reused answer"}}],
                  "usage": {"prompt_tokens_details": {
                      "cached_tokens": 111, "cache_write_tokens": 0,
                  }}},
        )
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-cloud-key")
    patch_transport(monkeypatch, handler)
    outcome = await providers.chat(
        MESSAGES, "anthropic/claude-test", "openrouter", False,
        provider_response_cache=True, provider_prompt_cache=True,
        cache_session_id="private-session-123",
    )
    headers, payload, target = captured[0]
    assert target == "https://openrouter.ai/api/v1/chat/completions"
    assert headers["authorization"] == "Bearer synthetic-cloud-key"
    assert headers["x-openrouter-cache"] == "true"
    assert headers["x-openrouter-cache-ttl"] == "300"
    assert payload["cache_control"] == {"type": "ephemeral"}
    assert payload["session_id"] == "private-session-123"
    assert payload["messages"] == MESSAGES
    assert outcome["provider_response_cache"] == {"requested": True, "status": "HIT"}
    assert outcome["provider_prompt_cache"]["reported_token_details"] == {}
    assert outcome["content"] == "reused answer"
    assert outcome["usage"] == {}
    assert "generation_id" not in outcome
    assert "synthetic-cloud-key" not in json.dumps(outcome)


@pytest.mark.asyncio
async def test_default_does_not_ask_provider_for_response_or_explicit_prompt_caches(monkeypatch):
    seen = []
    def handler(request):
        seen.append((request.headers, json.loads(request.content)))
        return httpx.Response(200, json={"choices": [
            {"message": {"content": "uncached answer"}}
        ]})
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    patch_transport(monkeypatch, handler)
    outcome = await providers.chat(MESSAGES, "openrouter/auto", "openrouter", False)
    headers, payload = seen[0]
    assert "x-openrouter-cache" not in headers
    assert "session_id" not in payload and "cache_control" not in payload
    assert "provider_response_cache" not in outcome
    assert "provider_prompt_cache" not in outcome


@pytest.mark.asyncio
async def test_missing_provider_cache_status_is_unknown_and_never_faked(monkeypatch):
    def handler(request):
        return httpx.Response(200, headers={"X-OpenRouter-Cache-Status": "INVENTED"},
                              json={"choices": [{"message": {"content": "answer"}}]})
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    patch_transport(monkeypatch, handler)
    outcome = await providers.chat(
        MESSAGES, "anthropic/claude-test", "openrouter", False,
        provider_response_cache=True,
    )
    assert outcome["provider_response_cache"]["status"] == "UNKNOWN"


@pytest.mark.asyncio
async def test_stream_passes_cache_headers_with_no_session_for_opt_out(monkeypatch):
    requests = []
    def handler(req):
        requests.append((dict(req.headers), json.loads(req.content)))
        return httpx.Response(
            200, headers={"X-OpenRouter-Cache-Status": "MISS"},
            text='data: {"id":"gen-streamA","model":"anthropic/demo",'
                 '"choices":[{"delta":{"content":"hi"}}],'
                 '"usage":{"prompt_tokens_details":{"cached_tokens":48}}}\n\n'
                 'data: [DONE]\n\n',
        )
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-only")
    patch_transport(monkeypatch, handler)
    events = [item async for item in providers.stream_chat(
        MESSAGES, "anthropic/demo", "openrouter",
        provider_response_cache=True, provider_prompt_cache=True,
        cache_session_id="session-12345678",
    )]
    assert events[0] == {"type": "delta", "content": "hi"}
    assert events[-1]["type"] == "done"
    assert events[-1]["provider_response_cache"]["status"] == "MISS"
    assert events[-1]["provider_prompt_cache"]["reported_token_details"] == {
        "cached_tokens": 48,
    }
    assert requests[0][0]["x-openrouter-cache"] == "true"
    assert requests[0][1]["cache_control"] == {"type": "ephemeral"}
    assert requests[0][1]["session_id"] == "session-12345678"


@pytest.mark.asyncio
async def test_redirect_failure_does_not_claim_cache_savings(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    patch_transport(monkeypatch, lambda req: httpx.Response(
        307, headers={"Location": "https://attacker.example/"}
    ))
    with pytest.raises(HTTPException) as failed:
        await providers.chat(
            MESSAGES, "anthropic/demo", "openrouter", False,
            provider_response_cache=True,
        )
    assert failed.value.status_code == 502


@pytest.mark.asyncio
async def test_max_output_limit_provider_specific_payloads(monkeypatch):
    seen = []
    def handler(req):
        parsed = json.loads(req.content)
        seen.append((str(req.url), parsed))
        if "/api/chat" in str(req.url):
            return httpx.Response(200, json={"model": "test-local-model",
                                             "message": {"content": "short"}})
        return httpx.Response(200, json={"choices": [
            {"message": {"content": "short"}}
        ]})
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OLLAMA_MODEL", "test-local-model")
    patch_transport(monkeypatch, handler)
    await providers.chat(MESSAGES, "anthropic/demo", "openrouter", False,
                         max_output_tokens=256)
    await providers.chat(MESSAGES, "local", "ollama", False,
                         max_output_tokens=256)
    assert seen[0][1]["max_tokens"] == 256
    assert seen[1][0] == "http://127.0.0.1:11434/api/chat"
    assert seen[1][1]["options"] == {"num_predict": 256}
    assert "options" not in seen[0][1]
