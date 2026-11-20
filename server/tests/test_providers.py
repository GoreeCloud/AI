import os
import pytest
from app import providers


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
