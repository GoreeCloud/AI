"""Explicit local Ollama summary preview and temporary reuse (synthetic data only)."""
import pytest
from fastapi.testclient import TestClient

from app import providers, token_savings
from app.main import app
from app.security import _ROUTE_CAPABILITIES

client = TestClient(app)
OWNER = {"Authorization": "Bearer test-owner-token"}


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "test-owner-token")
    monkeypatch.setenv("OLLAMA_MODEL", "synthetic-local-model")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.delenv("GOREECLOUD_AI_ALLOW_REMOTE_OLLAMA", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    token_savings.summary_cache.clear()
    yield
    token_savings.summary_cache.clear()


def history():
    return [
        {"role": "system", "content": "Secret system rule stays out of summary"},
        {"role": "user", "content": "Early notes about pine canopies"},
        {"role": "assistant", "content": "Observed pine canopy detail"},
        {"role": "user", "content": "More context on pine trees"},
        {"role": "assistant", "content": "Tree note A"},
        {"role": "user", "content": "Latest context B"},
        {"role": "assistant", "content": "Latest answer C"},
        {"role": "user", "content": "Newest question D"},
    ]


def payload(**kwargs):
    return {
        "messages": history(), "retain_last_messages": 4,
        "approved": True, **kwargs,
    }


def test_approval_owner_and_strict_scoped_route(monkeypatch):
    async def no_model(*_args, **_kwargs):
        raise AssertionError("Refused request must not reach a provider")
    monkeypatch.setattr(providers, "chat", no_model)
    assert client.post("/api/v1/chat/local-summary", json=payload()).status_code == 401
    assert client.post("/api/v1/chat/local-summary", headers=OWNER,
                       json={**payload(), "approved": False}).status_code == 403
    assert _ROUTE_CAPABILITIES[("POST", "/api/v1/chat/local-summary")] == "inference"


def test_local_summary_excludes_system_and_recent_messages(monkeypatch):
    calls = []
    async def summarize(data, model, provider, fallback, **kwargs):
        calls.append((data, model, provider, fallback, kwargs))
        return {"provider": "ollama", "model": "synthetic-local-model",
                "content": "Provisional summary of pine canopy details"}
    monkeypatch.setattr(providers, "chat", summarize)
    answer = client.post("/api/v1/chat/local-summary", headers=OWNER, json=payload())
    assert answer.status_code == 200
    body = answer.json()
    assert body["summary"].startswith("Provisional")
    assert body["sent_to_cloud"] is False
    assert body["saved_to_disk"] is False
    assert body["auto_applied"] is False
    assert body["may_contain_errors"] is True
    assert body["older_messages"] == 3
    args = calls[0]
    assert args[1:] == ("local", "ollama", False, {"max_output_tokens": 384})
    assert len(args[0]) == 2
    assert args[0][0]["role"] == "system"
    assert "Secret system rule" not in str(args[0])
    assert "Newest question D" not in str(args[0])
    assert "pine canopies" in args[0][1]["content"]
    assert "openrouter" not in str(args[0]).lower()
    assert "Provisional" in body["summary"]


def test_repeated_summaries_only_reused_with_explicit_opt_in(monkeypatch):
    count = []
    async def summarize(*_args, **_kwargs):
        count.append(1)
        return {"provider": "ollama", "model": "synthetic-local-model",
                "content": f"Provisional draft {len(count)}"}
    monkeypatch.setattr(providers, "chat", summarize)
    for _ in range(2):
        reply = client.post("/api/v1/chat/local-summary", headers=OWNER, json=payload())
        assert reply.status_code == 200
        assert "cache" not in reply.json()
    assert len(count) == 2
    opts = payload(reuse_local_summary_cache=True)
    first = client.post("/api/v1/chat/local-summary", headers=OWNER, json=opts)
    second = client.post("/api/v1/chat/local-summary", headers=OWNER, json=opts)
    assert first.status_code == second.status_code == 200
    assert first.json()["cache"]["hit"] is False
    assert second.json()["cache"]["hit"] is True
    assert second.json()["cache"]["provider_contacted"] is False
    assert second.json()["summary"] == first.json()["summary"]
    assert len(count) == 3
    status = client.get("/api/v1/cache/status", headers=OWNER)
    assert status.status_code == 200
    assert status.json()["summaries"]["entries"] == 1
    assert "Provisional draft 3" not in status.text
    assert status.headers["cache-control"] == "no-store"
    assert client.post("/api/v1/cache/clear", headers=OWNER, json={}).status_code == 403
    cleared = client.post("/api/v1/cache/clear", headers=OWNER, json={"approved": True})
    assert cleared.status_code == 200
    assert cleared.json()["summaries_cleared"] == 1
    assert client.get("/api/v1/cache/status", headers=OWNER).json()["summaries"]["entries"] == 0


def test_cache_key_partitions_source_versions(monkeypatch):
    count = []
    async def summarize(*_args, **_kwargs):
        count.append(1)
        return {"provider": "ollama", "model": "local", "content": "Summary " + str(len(count))}
    monkeypatch.setattr(providers, "chat", summarize)
    options = payload(reuse_local_summary_cache=True)
    assert client.post("/api/v1/chat/local-summary", headers=OWNER,
                       json=options).json()["cache"]["hit"] is False
    modified = history()
    modified[1]["content"] = "Changed pine forest facts"
    answer = client.post("/api/v1/chat/local-summary", headers=OWNER,
                         json={**options, "messages": modified})
    assert answer.json()["cache"]["hit"] is False
    assert len(count) == 2


def test_loopback_only_rejects_operator_approved_remote_ollama(monkeypatch):
    async def never(*_args, **_kwargs):
        raise AssertionError("Network must remain unused")
    monkeypatch.setattr(providers, "chat", never)
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://remote-ollama.example:11434")
    monkeypatch.setenv("GOREECLOUD_AI_ALLOW_REMOTE_OLLAMA", "true")
    result = client.post("/api/v1/chat/local-summary", headers=OWNER, json=payload())
    assert result.status_code == 503
    assert "loopback" in result.text
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://attacker.example:11434")
    assert client.post("/api/v1/chat/local-summary", headers=OWNER,
                       json=payload()).status_code == 503


def test_missing_local_model_and_empty_older_history_are_refused(monkeypatch):
    async def never(*_args, **_kwargs):
        raise AssertionError("No inference should run")
    monkeypatch.setattr(providers, "chat", never)
    monkeypatch.delenv("OLLAMA_MODEL")
    assert client.post("/api/v1/chat/local-summary", headers=OWNER,
                       json=payload()).status_code == 503
    monkeypatch.setenv("OLLAMA_MODEL", "synthetic-local-model")
    short = [{"role": "user", "content": "Current question"},
             {"role": "assistant", "content": "Current answer"}]
    assert client.post("/api/v1/chat/local-summary", headers=OWNER, json={
        "messages": short, "approved": True
    }).status_code == 422


def test_old_context_limits_and_invalid_input_bounds(monkeypatch):
    async def never(*_args, **_kwargs):
        raise AssertionError("No inference should run")
    monkeypatch.setattr(providers, "chat", never)
    oversized = [{"role": "user", "content": "x" * 13500}] + history()
    assert client.post("/api/v1/chat/local-summary", headers=OWNER,
                       json={**payload(), "messages": oversized}).status_code == 413
    assert client.post("/api/v1/chat/local-summary", headers=OWNER,
                       json={**payload(), "retain_last_messages": 17}).status_code == 422
    assert client.post("/api/v1/chat/local-summary", headers=OWNER,
                       json={**payload(), "retain_last_messages": 0}).status_code == 422


@pytest.mark.parametrize("bad", ["", "x" * 2401])
def test_model_response_validated(monkeypatch, bad):
    async def summarize(*_args, **_kwargs):
        return {"provider": "ollama", "model": "local", "content": bad}
    monkeypatch.setattr(providers, "chat", summarize)
    response = client.post("/api/v1/chat/local-summary", headers=OWNER,
                           json=payload(reuse_local_summary_cache=True))
    assert response.status_code == 502
    assert client.get("/api/v1/cache/status", headers=OWNER).json()["summaries"]["entries"] == 0


def test_rejects_unexpected_local_provider_response(monkeypatch):
    async def invalid(*_args, **_kwargs):
        return {"provider": "openrouter", "model": "remote", "content": "wrong"}
    monkeypatch.setattr(providers, "chat", invalid)
    reply = client.post("/api/v1/chat/local-summary", headers=OWNER, json=payload())
    assert reply.status_code == 502
    assert "wrong" not in reply.text
