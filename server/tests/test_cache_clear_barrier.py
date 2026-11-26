"""Synthetic tests for cache invalidation during inference and selective clearing."""
import json

import pytest
from fastapi.testclient import TestClient

from app import providers, storage, token_savings
from app.main import app

client = TestClient(app)
OWNER = {"Authorization": "Bearer test-owner-token"}
ANSWER = {"content": "Synthetic reply", "provider": "ollama", "model": "local"}
STORES = {
    "chat": token_savings.response_cache,
    "research": token_savings.research_cache,
    "summaries": token_savings.summary_cache,
}


@pytest.fixture(autouse=True)
def owner(monkeypatch, tmp_path):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "test-owner-token")
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(tmp_path / "cache.sqlite3"))
    monkeypatch.setenv("OLLAMA_MODEL", "synthetic-model")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    for store in STORES.values():
        store.clear()
    yield
    for store in STORES.values():
        store.clear()


def clear(selection):
    result = client.post("/api/v1/cache/clear", headers=OWNER,
                         json={"approved": True, "selection": selection})
    assert result.status_code == 200
    return result.json()


@pytest.mark.parametrize("selection", ["chat", "research", "summaries", "all"])
def test_selective_clear_and_stale_admissions(selection):
    epochs = {}
    for name, store in STORES.items():
        _, epoch = store.lookup("existing")
        assert store.put("existing", ANSWER, epoch=epoch)
        _, epochs[name] = store.lookup("pending")
    result = clear(selection)
    assert result["selection"] == selection
    assert client.get("/api/v1/cache/status", headers=OWNER).json()["selective_clear_supported"]
    assert result["cleared"] == (3 if selection == "all" else 1)
    for name, store in STORES.items():
        targeted = selection in ("all", name)
        assert (store.get("existing") is None) == targeted
        assert store.put("pending", ANSWER, epoch=epochs[name]) != targeted
        assert store.status()["invalidated_writes"] == int(targeted)
        _, epoch = store.lookup("new")
        assert store.put("new", ANSWER, epoch=epoch)


def test_clear_requires_auth_approval_and_valid_selection():
    path = "/api/v1/cache/clear"
    assert client.post(path, json={"approved": True}).status_code == 401
    assert client.post(path, headers=OWNER, json={"selection": "chat"}).status_code == 403
    assert client.post(path, headers=OWNER,
                       json={"approved": True, "selection": "unknown"}).status_code == 422


@pytest.mark.parametrize("route,selection", [
    ("chat", "chat"),
    ("chat/stream", "chat"),
    ("chat/local-summary", "summaries"),
    ("research/answer", "research"),
])
def test_clear_during_inference_does_not_repopulate(monkeypatch, route, selection):
    calls = []
    async def mocked(*_args, **_kwargs):
        calls.append(1)
        if len(calls) == 1:
            clear(selection)
        return ANSWER.copy()

    async def stream(*_args, **_kwargs):
        calls.append(1)
        yield {"type": "delta", "content": ANSWER["content"]}
        if len(calls) == 1:
            clear(selection)
        yield {"type": "done", "provider": "ollama", "model": "local",
               "upstream_terminal": True}

    monkeypatch.setattr(providers, "chat", mocked)
    monkeypatch.setattr(providers, "stream_chat", stream)
    messages = [{"role": "user", "content": "Synthetic old question"},
                {"role": "assistant", "content": "Synthetic answer"},
                {"role": "user", "content": "Synthetic next question"}]
    payload = {"messages": messages, "provider": "ollama", "model": "local",
               "local_response_cache": True}
    if selection == "summaries":
        payload = {"messages": messages, "retain_last_messages": 1,
                   "approved": True, "reuse_local_summary_cache": True}
    if selection == "research":
        storage.create_document("Moon craters", "Moon craters are visible.")
        payload = {"question": "moon craters", "provider": "ollama",
                   "local_answer_cache": True}

    def request():
        response = client.post("/api/v1/" + route, headers=OWNER, json=payload)
        assert response.status_code == 200
        if route == "chat/stream":
            return [json.loads(line[6:]) for line in response.text.splitlines()
                    if line.startswith("data: ")][-1]["cache"]
        return response.json()["cache"]

    assert request()["stored"] is False
    assert STORES[selection].status()["entries"] == 0
    assert request()["stored"] is True
    assert request()["hit"] is True
    assert len(calls) == 2
