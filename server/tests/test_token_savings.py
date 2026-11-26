"""Synthetic-only token saving tests: no network, secrets, or user data."""
import pytest
from fastapi.testclient import TestClient

from app import providers, storage, token_savings
from app.main import app
from app.security import _ROUTE_CAPABILITIES

client = TestClient(app)
OWNER = {"Authorization": "Bearer test-owner-token"}
USER_TEXT = {"role": "user", "content": "Example prompt that remains private"}


@pytest.fixture(autouse=True)
def owner_environment(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "test-owner-token")
    monkeypatch.setenv("OLLAMA_MODEL", "test-local-model")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    token_savings.response_cache.clear()
    yield
    token_savings.response_cache.clear()


def _body(**kwargs):
    return {
        "messages": [USER_TEXT], "provider": "ollama", "model": "local",
        "allow_cloud_processing": False, **kwargs,
    }


def test_preview_is_local_counts_only_preserves_system_in_original_order(monkeypatch):
    monkeypatch.setattr(providers, "chat", lambda *_args: pytest.fail("No model request allowed"))
    history = [
        {"role": "system", "content": "Stable behavior instruction"},
        {"role": "user", "content": "History one" * 30},
        {"role": "assistant", "content": "First answer" * 30},
        {"role": "user", "content": "History two" * 30},
        {"role": "assistant", "content": "Second answer" * 30},
        {"role": "user", "content": "Newest user question"},
    ]
    reduced = token_savings.select_context(history, "last_n", 2)
    assert reduced == [history[0], history[-2], history[-1]]
    report = client.post("/api/v1/chat/context-preview", headers=OWNER,
                         json={**_body(), "messages": history,
                               "context_mode": "last_n", "context_messages": 2})
    assert report.status_code == 200
    result = report.json()
    assert result["messages_original"] == 6
    assert result["messages_sent"] == 3
    assert result["messages_omitted"] == 3
    assert result["estimated_input_tokens_reduced"] > 0
    assert result["sent_to_provider"] is False
    assert result["saved_to_disk"] is False
    assert "Stable behavior instruction" not in report.text
    assert client.post("/api/v1/chat/context-preview", json=_body()).status_code == 401
    assert client.post("/api/v1/chat/context-preview", headers=OWNER, json={
        **_body(), "context_messages": 33,
    }).status_code == 422


def test_cache_reuse_only_after_explicit_request_and_no_stale_usage(monkeypatch):
    called = []
    async def mocked(history, model, selected, fallback):
        called.append((history, model, selected, fallback))
        return {
            "content": "Safe synthetic answer", "model": "test-local-model",
            "provider": "ollama", "usage": {"total_tokens": 999},
            "generation_id": "gen-old",
        }
    monkeypatch.setattr(providers, "chat", mocked)
    # Disabled by default, including exact repeated requests.
    assert client.post("/api/v1/chat", headers=OWNER, json=_body()).status_code == 200
    assert client.post("/api/v1/chat", headers=OWNER, json=_body()).status_code == 200
    assert len(called) == 2
    first = client.post("/api/v1/chat", headers=OWNER,
                        json=_body(local_response_cache=True))
    second = client.post("/api/v1/chat", headers=OWNER,
                         json=_body(local_response_cache=True))
    assert first.status_code == second.status_code == 200
    assert first.json()["cache"] == {
        "mode": "local-process-memory", "hit": False,
        "stored": True, "provider_contacted": True,
    }
    cached = second.json()
    assert cached["cache"]["hit"] is True
    assert cached["cache"]["provider_contacted"] is False
    assert cached["usage"] == {}
    assert "generation_id" not in cached
    assert cached["content"] == "Safe synthetic answer"
    assert len(called) == 3
    status = client.get("/api/v1/cache/status", headers=OWNER)
    assert status.json()["entries"] == 1
    assert status.json()["hits"] == 1
    assert "Safe synthetic answer" not in status.text
    assert status.headers["cache-control"] == "no-store"
    assert client.get("/api/v1/cache/status").status_code == 401


def test_ttl_clear_and_distinct_request_keys(monkeypatch):
    current = [10_000.0]
    monkeypatch.setattr(token_savings.time, "monotonic", lambda: current[0])
    calls = []
    async def mocked(history, *_args):
        calls.append(history[-1]["content"])
        return {"provider": "ollama", "model": "m", "content": "reply"}
    monkeypatch.setattr(providers, "chat", mocked)
    root = _body(local_response_cache=True)
    assert client.post("/api/v1/chat", headers=OWNER, json=root).json()["cache"]["hit"] is False
    changed = {**root, "messages": [{"role": "user", "content": "Another request"}]}
    assert client.post("/api/v1/chat", headers=OWNER, json=changed).json()["cache"]["hit"] is False
    assert len(calls) == 2
    current[0] += token_savings.TTL_SECONDS + 1
    assert client.post("/api/v1/chat", headers=OWNER, json=root).json()["cache"]["hit"] is False
    assert len(calls) == 3
    assert client.post("/api/v1/cache/clear", headers=OWNER, json={}).status_code == 403
    assert client.post("/api/v1/cache/clear", json={"approved": True}).status_code == 401
    cleared = client.post("/api/v1/cache/clear", headers=OWNER,
                          json={"approved": True})
    assert cleared.status_code == 200
    assert cleared.json()["cleared"] == 1
    assert client.get("/api/v1/cache/status", headers=OWNER).json()["entries"] == 0
    assert client.post("/api/v1/chat", headers=OWNER, json=root).json()["cache"]["hit"] is False


def test_cache_capacity_and_bounds():
    instance = token_savings.ResponseCache()
    for i in range(70):
        _, epoch = instance.lookup(str(i))
        assert instance.put(str(i), {"provider": "ollama", "model": "m", "content": "ok"},
                            epoch=epoch)
    assert instance.status()["entries"] == token_savings.MAX_ENTRIES
    assert instance.get("0") is None
    _, epoch = instance.lookup("bad")
    assert not instance.put("bad", {"provider": "ollama", "model": "m", "content": ""},
                            epoch=epoch)
    assert not instance.put("huge", {"provider": "ollama", "model": "m",
                                     "content": "x" * 120_001}, epoch=epoch)


@pytest.mark.parametrize("fields", [
    {"provider_response_cache": True},
    {"provider_prompt_cache": True},
    {"cache_session_id": "session-12345678"},
])
def test_provider_caching_requires_openrouter_and_local_refusal(fields):
    answer = client.post("/api/v1/chat", headers=OWNER, json={**_body(), **fields})
    assert answer.status_code == 422


def test_no_provider_prompt_cache_for_other_models_and_invalid_session(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key-only")
    base = {"provider": "openrouter", "allow_cloud_processing": True}
    rejected = client.post("/api/v1/chat", headers=OWNER,
                           json={**_body(), **base, "model": "openai/example",
                                 "provider_prompt_cache": True})
    assert rejected.status_code == 422
    assert client.post("/api/v1/chat", headers=OWNER,
                       json={**_body(), **base, "cache_session_id": "../url"}).status_code == 422


def test_cloud_consent_and_actual_upstream_admission_on_cache_hit(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key-only")
    admissions = []
    async def budget():
        admissions.append("key")
    def admit(kind, approved):
        assert approved and kind == "chat"
        admissions.append("admit")
    async def model(history, *_args):
        admissions.append("provider")
        return {"provider": "openrouter", "model": "anthropic/test", "content": "answer"}
    monkeypatch.setattr(providers, "verify_cloud_key_budget", budget)
    monkeypatch.setattr(storage, "admit_cloud_call", admit)
    monkeypatch.setattr(providers, "chat", model)
    data = {**_body(), "provider": "openrouter", "model": "anthropic/test",
            "allow_cloud_processing": True, "local_response_cache": True}
    assert client.post("/api/v1/chat", headers=OWNER, json=data).json()["cache"]["hit"] is False
    assert client.post("/api/v1/chat", headers=OWNER, json=data).json()["cache"]["hit"] is True
    assert admissions == ["key", "admit", "provider"]
    denied = {**data, "allow_cloud_processing": False}
    assert client.post("/api/v1/chat", headers=OWNER, json=denied).status_code == 403
    assert admissions == ["key", "admit", "provider"]


def test_fallback_does_not_populate_cloud_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-remote")
    async def budget():
        return None
    async def output(*_args, **_kwargs):
        return {"provider": "ollama", "model": "test-local-model", "content": "local fallback"}
    monkeypatch.setattr(providers, "verify_cloud_key_budget", budget)
    monkeypatch.setattr(storage, "admit_cloud_call", lambda *_args, **_kw: None)
    monkeypatch.setattr(providers, "chat", output)
    data = {**_body(), "provider": "openrouter", "allow_cloud_processing": True,
            "allow_local_fallback": True, "local_response_cache": True}
    result = client.post("/api/v1/chat", headers=OWNER, json=data)
    assert result.status_code == 200
    assert result.json()["cache"]["stored"] is False
    assert client.get("/api/v1/cache/status", headers=OWNER).json()["entries"] == 0


def test_stream_cache_respects_strict_capability_matrix():
    # Successful opt-in SSE replay and provider completion are exercised by
    # test_stream_response_cache.py; preserve the read/admin route matrix.
    assert _ROUTE_CAPABILITIES[("POST", "/api/v1/chat/context-preview")] == "read"
    assert _ROUTE_CAPABILITIES[("GET", "/api/v1/cache/status")] == "read"
    assert _ROUTE_CAPABILITIES[("POST", "/api/v1/cache/clear")] == "admin"


def test_output_cap_validation_and_cache_partition(monkeypatch):
    answers = []
    async def mocked(history, model, selected, fallback, **kwargs):
        answers.append(kwargs["max_output_tokens"])
        return {"provider": "ollama", "model": "test-local-model", "content": "answer"}
    monkeypatch.setattr(providers, "chat", mocked)
    for cap in (256, 512):
        for _ in range(2):
            result = client.post("/api/v1/chat", headers=OWNER,
                                 json=_body(local_response_cache=True, max_output_tokens=cap))
            assert result.status_code == 200
    assert answers == [256, 512]  # Each cap has its own cache key.
    assert client.post("/api/v1/chat", headers=OWNER,
                       json=_body(max_output_tokens=63)).status_code == 422
    assert client.post("/api/v1/chat", headers=OWNER,
                       json=_body(max_output_tokens=2049)).status_code == 422


def test_actual_trimmed_message_list_reaches_model(monkeypatch):
    seen = []
    async def mocked(history, *_args, **_kwargs):
        seen.append(history)
        return {"provider": "ollama", "model": "test-local-model", "content": "result"}
    monkeypatch.setattr(providers, "chat", mocked)
    history = [
        {"role": "system", "content": "Keep invariant instruction"},
        {"role": "user", "content": "Old irrelevant private info"},
        {"role": "assistant", "content": "Old response"},
        {"role": "user", "content": "New request"},
    ]
    result = client.post("/api/v1/chat", headers=OWNER,
                         json={**_body(), "messages": history,
                               "context_mode": "last_n", "context_messages": 1})
    assert result.status_code == 200
    assert seen == [[history[0], history[-1]]]
    assert "Old irrelevant private info" not in str(seen)
