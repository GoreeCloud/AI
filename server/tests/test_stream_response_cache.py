"""Opt-in full-stream SSE cache reuse; only provider-terminal completions persist."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import providers, storage, token_savings
from app.main import app

client = TestClient(app)
OWNER = {"Authorization": "Bearer test-owner-token"}


@pytest.fixture(autouse=True)
def owner(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "test-owner-token")
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("OLLAMA_MODEL", "synthetic-local-model")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    token_savings.response_cache.clear()
    yield
    token_savings.response_cache.clear()


def body(**options):
    return {"messages": [{"role": "user", "content": "Synthetic SSE answer request"}],
            "provider": "ollama", "model": "local", **options}


def stream_events(response):
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    return [json.loads(row[6:]) for row in response.text.splitlines()
            if row.startswith("data: ")]


def test_opt_in_stream_replays_completed_answer_without_provider_call(monkeypatch):
    calls = []
    async def source(messages, model, provider, **kwargs):
        calls.append(kwargs)
        yield {"type": "delta", "content": "First "}
        yield {"type": "delta", "content": "second"}
        yield {"type": "done", "provider": "ollama", "model": "synthetic-local-model",
               "upstream_terminal": True}
    monkeypatch.setattr(providers, "stream_chat", source)
    first = stream_events(client.post("/api/v1/chat/stream", headers=OWNER,
                                      json=body(local_response_cache=True)))
    second = stream_events(client.post("/api/v1/chat/stream", headers=OWNER,
                                       json=body(local_response_cache=True)))
    assert len(calls) == 1
    assert calls[0]["expose_terminal"] is True
    assert first[-1]["cache"]["stored"] is True
    assert second == [
        {"type": "delta", "content": "First second"},
        {"type": "done", "provider": "ollama", "model": "synthetic-local-model",
         "cache": {"mode": "local-process-memory", "hit": True,
                   "provider_contacted": False, "new_usage_reported": False}},
    ]
    assert client.get("/api/v1/cache/status", headers=OWNER).json()["entries"] == 1


def test_stream_no_cache_by_default_preserves_old_provider_invocation(monkeypatch):
    calls = []
    async def source(messages, model, provider):
        calls.append(1)
        yield {"type": "delta", "content": "live"}
        yield {"type": "done", "provider": "ollama", "model": "local"}
    monkeypatch.setattr(providers, "stream_chat", source)
    for _ in range(2):
        response = stream_events(client.post("/api/v1/chat/stream", headers=OWNER,
                                             json=body()))
        assert "cache" not in response[-1]
    assert len(calls) == 2
    assert client.get("/api/v1/cache/status", headers=OWNER).json()["entries"] == 0


@pytest.mark.parametrize("terminal", [False, None])
def test_incomplete_or_unconfirmed_upstream_stream_is_never_stored(monkeypatch, terminal):
    calls = []
    async def source(*_args, **_kwargs):
        calls.append(1)
        yield {"type": "delta", "content": "partial"}
        event = {"type": "done", "provider": "ollama", "model": "local"}
        if terminal is not None:
            event["upstream_terminal"] = terminal
        yield event
    monkeypatch.setattr(providers, "stream_chat", source)
    opts = body(local_response_cache=True)
    for _ in range(2):
        result = stream_events(client.post("/api/v1/chat/stream", headers=OWNER, json=opts))
        assert result[-1]["cache"]["stored"] is False
    assert len(calls) == 2
    assert client.get("/api/v1/cache/status", headers=OWNER).json()["entries"] == 0


def test_stream_error_does_not_store_partial_response(monkeypatch):
    count = []
    async def source(*_args, **_kwargs):
        count.append(1)
        yield {"type": "delta", "content": "partial answer"}
        yield {"type": "error", "message": "provider interrupted"}
    monkeypatch.setattr(providers, "stream_chat", source)
    opts = body(local_response_cache=True)
    for _ in range(2):
        result = stream_events(client.post("/api/v1/chat/stream", headers=OWNER, json=opts))
        assert result[-1]["type"] == "error"
    assert len(count) == 2
    assert client.get("/api/v1/cache/status", headers=OWNER).json()["entries"] == 0


def test_sse_cache_hit_requires_cloud_consent_and_skips_new_admission(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    record = []
    async def budget():
        record.append("budget")
    def admitted(kind, approved):
        assert approved and kind == "chat-stream"
        record.append("admit")
    async def source(*_args, **_kwargs):
        record.append("provider")
        yield {"type": "delta", "content": "cloud result"}
        yield {"type": "done", "provider": "openrouter", "model": "test-model",
               "upstream_terminal": True, "generation_id": "gen-old"}
    monkeypatch.setattr(providers, "verify_cloud_key_budget", budget)
    monkeypatch.setattr(storage, "admit_cloud_call", admitted)
    monkeypatch.setattr(providers, "stream_chat", source)
    opts = {**body(local_response_cache=True), "provider": "openrouter",
            "allow_cloud_processing": True}
    a = stream_events(client.post("/api/v1/chat/stream", headers=OWNER, json=opts))
    b = stream_events(client.post("/api/v1/chat/stream", headers=OWNER, json=opts))
    assert a[-1]["cache"]["stored"] is True
    assert b[-1]["cache"]["hit"] is True
    assert "generation_id" not in b[-1]
    assert record == ["budget", "admit", "provider"]
    denied = {**opts, "allow_cloud_processing": False}
    assert client.post("/api/v1/chat/stream", headers=OWNER, json=denied).status_code == 403
    assert client.post("/api/v1/chat/stream", json=opts).status_code == 401
    assert record == ["budget", "admit", "provider"]


def test_nonstream_saved_answer_can_be_replayed_as_sse(monkeypatch):
    async def answer(*_args):
        return {"provider": "ollama", "model": "local", "content": "complete reply"}
    async def never(*_args, **_kwargs):
        raise AssertionError("Complete answer cache hit must not open an upstream stream")
        yield {}
    monkeypatch.setattr(providers, "chat", answer)
    request = body(local_response_cache=True)
    created = client.post("/api/v1/chat", headers=OWNER, json=request)
    assert created.json()["cache"]["stored"] is True
    monkeypatch.setattr(providers, "stream_chat", never)
    result = stream_events(client.post("/api/v1/chat/stream", headers=OWNER, json=request))
    assert result[-1]["cache"]["hit"] is True
    assert "".join(e["content"] for e in result if e["type"] == "delta") == "complete reply"


def test_output_length_forms_independent_stream_cache_keys(monkeypatch):
    counted = []
    async def source(*_args, **_kwargs):
        counted.append(1)
        yield {"type": "delta", "content": "short reply"}
        yield {"type": "done", "provider": "ollama", "model": "local",
               "upstream_terminal": True}
    monkeypatch.setattr(providers, "stream_chat", source)
    for cap in (256, 512):
        opts = body(local_response_cache=True, max_output_tokens=cap)
        assert stream_events(client.post("/api/v1/chat/stream", headers=OWNER,
                                         json=opts))[-1]["cache"]["stored"] is True
        assert stream_events(client.post("/api/v1/chat/stream", headers=OWNER,
                                         json=opts))[-1]["cache"]["hit"] is True
    assert len(counted) == 2
    assert client.post("/api/v1/chat/stream", headers=OWNER,
                       json=body(allow_local_fallback=True)).status_code == 422


@pytest.mark.asyncio
async def test_ollama_provider_exposes_terminal_only_when_requested(monkeypatch):
    original = httpx.AsyncClient
    def fixture(_request):
        return httpx.Response(200, text=(
            '{"model":"demo","message":{"content":"one"},"done":false}\n'
            '{"model":"demo","message":{"content":"two"},"done":true}\n'
        ))
    monkeypatch.setenv("OLLAMA_MODEL", "demo")
    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: original(transport=httpx.MockTransport(fixture), **kwargs))
    output = [e async for e in providers.stream_chat(
        [{"role": "user", "content": "hi"}], "local", "ollama", expose_terminal=True,
    )]
    assert output[-1]["upstream_terminal"] is True
    assert "".join(e["content"] for e in output if e["type"] == "delta") == "onetwo"


def test_eof_without_provider_terminal_is_not_cache_eligible(monkeypatch):
    original = httpx.AsyncClient
    monkeypatch.setenv("OLLAMA_MODEL", "demo")
    upstream_calls = []

    def fixture(request):
        upstream_calls.append(request)
        return httpx.Response(
            200, text='{"model":"demo","message":{"content":"partial"},"done":false}\n',
        )

    monkeypatch.setattr(providers.httpx, "AsyncClient",
                        lambda **kwargs: original(transport=httpx.MockTransport(fixture), **kwargs))
    request = body(local_response_cache=True)
    for _ in range(2):
        events = stream_events(client.post("/api/v1/chat/stream", headers=OWNER, json=request))
        assert events == [
            {"type": "delta", "content": "partial"},
            {"type": "error", "message": "Model stream stopped before completion"},
        ]
    assert len(upstream_calls) == 2
    assert client.get("/api/v1/cache/status", headers=OWNER).json()["entries"] == 0
