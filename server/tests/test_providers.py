import httpx
import pytest
from fastapi.testclient import TestClient

from app import providers, token_savings
from app.main import app


@pytest.fixture
def call_nonstream_chat(monkeypatch, tmp_path):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "synthetic-owner")
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(tmp_path / "chat.sqlite"))
    monkeypatch.setenv("GOREECLOUD_AI_REQUIRE_CAPPED_OPENROUTER_KEY", "false")
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    monkeypatch.setenv("OLLAMA_MODEL", "mock-local")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    response_cache = token_savings.ResponseCache()
    monkeypatch.setattr(token_savings, "response_cache", response_cache)
    client_type = httpx.AsyncClient

    def call(provider, upstream_body, *, cache=False):
        expected_url = ("https://openrouter.ai/api/v1/chat/completions" if provider == "openrouter"
                        else "http://127.0.0.1:11434/api/chat")
        requests = []

        def handle(request):
            requests.append(str(request.url))
            return httpx.Response(200, text=upstream_body)

        monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: client_type(
            transport=httpx.MockTransport(handle), **kwargs,
        ))
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/chat", headers={"Authorization": "Bearer synthetic-owner"}, json={
                    "messages": [{"role": "user", "content": "synthetic prompt"}],
                    "provider": provider,
                    "allow_cloud_processing": provider == "openrouter",
                    "allow_local_fallback": True,
                    "local_response_cache": cache,
                },
            )
        assert requests == [expected_url]
        return response, response_cache.status()["entries"]

    return call


@pytest.mark.parametrize(("provider", "upstream_body"), [
    ("openrouter", '{"choices":{"unexpected":"private synthetic provider detail"}}'),
    ("openrouter", '{"choices":["private synthetic provider detail"]}'),
    ("openrouter", '{"choices":[{"message":"private synthetic provider detail"}]}'),
    ("ollama", '{"message":"private synthetic provider detail"}'),
    ("ollama", '{"message":{"content":["private synthetic provider detail"]}}'),
    ("ollama", '{"message":{}}'),
    ("ollama", r'{"message":{"content":"\ud800"}}'),
], ids=[
    "choices-object", "choice-string", "cloud-message-string", "local-message-string",
    "local-nontext", "missing-local-text", "invalid-unicode",
])
def test_malformed_nonstream_reply_fails_without_fallback_or_cache(call_nonstream_chat, provider, upstream_body):
    response, entries = call_nonstream_chat(provider, upstream_body, cache=True)
    assert response.status_code == 502
    assert "private synthetic provider detail" not in response.text
    assert entries == 0


@pytest.mark.parametrize(("metadata", "expected_model", "expected_usage"), [
    (
        '"model":"mock/model","usage":{"prompt_tokens":12,"prompt_tokens_details":{"cached_tokens":2}}',
        "mock/model",
        {"prompt_tokens": 12, "prompt_tokens_details": {"cached_tokens": 2}},
    ),
    ('"model":["invalid"],"usage":[1]', "openrouter/auto", {}),
    (r'"model":"\ud800","usage":{"cost":1e999}', "openrouter/auto", {}),
    (r'"usage":{"details":"\ud800"}', "openrouter/auto", {}),
])
def test_nonstream_reply_normalizes_invalid_optional_metadata(
    call_nonstream_chat, metadata, expected_model, expected_usage,
):
    upstream_body = '{"choices":[{"message":{"content":"valid answer"}}],' + metadata + "}"
    response, _ = call_nonstream_chat("openrouter", upstream_body)
    assert response.status_code == 200
    assert response.json() == {
        "provider": "openrouter", "model": expected_model, "content": "valid answer", "usage": expected_usage,
    }


@pytest.mark.asyncio
async def test_explicit_ollama_with_default_model(monkeypatch):
    async def stub(url, body, key=None, timeout=90.0):
        assert url == "http://127.0.0.1:11434/api/chat"
        assert body["model"] == "qwen3:4b"
        return {"model": "qwen3:4b", "message": {"content": "hello from local"}}

    monkeypatch.setattr(providers, "_post", stub)
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:4b")
    result = await providers.chat([{"role": "user", "content": "hi"}],
                                  "openrouter/auto", "ollama", False)
    assert result["provider"] == "ollama"
    assert result["content"] == "hello from local"


@pytest.mark.asyncio
async def test_openrouter_prioritized(monkeypatch):
    async def fake_post(url, body, key=None, timeout=90.0):
        assert url == "https://openrouter.ai/api/v1/chat/completions"
        assert body["model"] == "openrouter/auto"
        assert key == "test-key"
        return {"model": "example/routed", "choices": [{"message": {"content": "ok"}}], "usage": {}}

    monkeypatch.setattr(providers, "_post", fake_post)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    result = await providers.chat([{"role": "user", "content": "hi"}], "openrouter/auto", "auto", False)
    assert result["provider"] == "openrouter"
    assert result["model"] == "example/routed"


@pytest.mark.asyncio
async def test_no_implicit_fallback(monkeypatch):
    async def failing(*args, **kwargs):
        raise providers.UpstreamFailure("openrouter", 502, transient=True)
    monkeypatch.setattr(providers, "_post", failing)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OLLAMA_MODEL", "small")
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        await providers.chat([{"role": "user", "content": "private"}],
                             "openrouter/auto", "auto", False)


@pytest.mark.asyncio
async def test_explicit_fallback(monkeypatch):
    async def stub(url, body, key=None, timeout=90.0):
        if "openrouter.ai" in url:
            raise providers.UpstreamFailure("openrouter", 503, transient=True)
        assert url == "http://127.0.0.1:11434/api/chat"
        assert body["model"] == "small"
        return {"model": "small", "message": {"content": "local"}}
    monkeypatch.setattr(providers, "_post", stub)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OLLAMA_MODEL", "small")
    result = await providers.chat([{"role": "user", "content": "hi"}],
                                  "openrouter/auto", "auto", True)
    assert result["provider"] == "ollama"
