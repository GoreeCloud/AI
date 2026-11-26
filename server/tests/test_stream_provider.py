"""Validate actual OpenRouter SSE and Ollama NDJSON parsers without network calls."""
import json

import pytest

from app import providers


class StreamResponse:
    def __init__(self, lines, status_code=200):
        self.lines = lines
        self.status_code = status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def aiter_lines(self):
        for line in self.lines:
            yield line


class StubClient:
    def __init__(self, lines, status_code=200):
        self.lines, self.status_code = lines, status_code

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def stream(self, method, url, json, headers):
        assert method == "POST"
        assert json["stream"] is True
        assert url.startswith(("https://openrouter.ai/api/v1/", "http://127.0.0.1:11434/"))
        return StreamResponse(self.lines, self.status_code)


@pytest.mark.asyncio
async def test_openrouter_sse(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    lines = [
        ': keepalive',
        'data: {"choices":[{"delta":{"role":"assistant","content":null}}]}',
        'data: ' + json.dumps({"model": "tested", "choices": [{"delta": {"content": "Hey"}}]}),
        'data: ' + json.dumps({"choices": [{"delta": {"content": " there"}}]}),
        'data: {"choices":[],"usage":{"completion_tokens":2}}',
        'data:[DONE]'
    ]
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: StubClient(lines))
    events = [event async for event in providers.stream_chat(
        [{"role": "user", "content": "hello"}], "openrouter/auto", "openrouter")]
    assert events == [
        {"type": "delta", "content": "Hey"},
        {"type": "delta", "content": " there"},
        {"type": "done", "provider": "openrouter", "model": "tested"},
    ]


@pytest.mark.asyncio
async def test_ollama_ndjson(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "mock-local")
    lines = [
        json.dumps({"model": "mock-local", "message": {"content": "Local"}, "done": False}),
        json.dumps({"model": "mock-local", "message": {"content": " OK"}, "done": True}),
    ]
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: StubClient(lines))
    events = [event async for event in providers.stream_chat(
        [{"role": "user", "content": "hello"}], "openrouter/auto", "ollama")]
    assert events[-1] == {"type": "done", "provider": "ollama", "model": "mock-local"}
    assert "".join(e["content"] for e in events if e["type"] == "delta") == "Local OK"


@pytest.mark.asyncio
async def test_stream_provider_status_redacted(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: StubClient([], 503))
    events = [event async for event in providers.stream_chat(
        [{"role": "user", "content": "secret"}], "openrouter/auto", "openrouter")]
    assert events == [{"type": "error", "message": "Inference provider returned an error"}]
    assert "secret" not in json.dumps(events)


@pytest.mark.asyncio
@pytest.mark.parametrize(("provider", "partial_line"), [
    ("openrouter", 'data: {"choices":[{"delta":{"content":"partial"}}]}'),
    ("ollama", '{"message":{"content":"partial"},"done":false}'),
])
@pytest.mark.parametrize("expose_terminal", [False, True])
async def test_eof_without_provider_terminal_reports_error(
    monkeypatch, provider, partial_line, expose_terminal,
):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    monkeypatch.setenv("OLLAMA_MODEL", "mock-local")
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: StubClient([partial_line]))
    events = [event async for event in providers.stream_chat(
        [{"role": "user", "content": "hello"}], "local", provider,
        expose_terminal=expose_terminal,
    )]
    assert events == [
        {"type": "delta", "content": "partial"},
        {"type": "error", "message": "Model stream stopped before completion"},
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(("provider", "invalid"), [
    ("openrouter", 'truncated JSON'),
    ("openrouter", '[]'),
    ("openrouter", '{"choices":{"unexpected":"private provider data"}}'),
    ("openrouter", '{"choices":["private provider data"]}'),
    ("openrouter", '{"choices":[{"delta":"private provider data"}]}'),
    ("openrouter", '{"choices":[{"delta":{"content":["private provider data"]}}]}'),
    ("ollama", 'truncated JSON'),
    ("ollama", 'true'),
    ("ollama", '{"message":"private provider data","done":true}'),
    ("ollama", '{"message":{"content":["private provider data"]},"done":true}'),
    ("ollama", '{"done":"true"}'),
])
async def test_malformed_provider_data_ends_stream_with_redacted_error(monkeypatch, provider, invalid):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    monkeypatch.setenv("OLLAMA_MODEL", "mock-local")
    if provider == "openrouter":
        lines = ['data: {"choices":[{"delta":{"content":"partial"}}]}',
                 'data: ' + invalid, 'data: [DONE]']
    else:
        lines = ['{"message":{"content":"partial"},"done":false}', invalid, '{"done":true}']
    monkeypatch.setattr(providers.httpx, "AsyncClient", lambda **kwargs: StubClient(lines))
    events = [event async for event in providers.stream_chat(
        [{"role": "user", "content": "hello"}], "local", provider, expose_terminal=True,
    )]
    assert events == [
        {"type": "delta", "content": "partial"},
        {"type": "error", "message": "Inference provider returned invalid stream data"},
    ]
