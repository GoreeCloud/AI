"""Research answer cache revalidates source versions on every opt-in read."""
import pytest
from fastapi.testclient import TestClient

from app import providers, storage, token_savings
from app.main import app

client = TestClient(app)
H = {"Authorization": "Bearer test-owner-token"}


@pytest.fixture(autouse=True)
def isolate_research_cache():
    token_savings.research_cache.clear()
    yield
    token_savings.research_cache.clear()


def setup(monkeypatch, tmp_path):
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "test-owner-token")
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(tmp_path / "research.sqlite3"))
    monkeypatch.setenv("OLLAMA_MODEL", "synthetic-model")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    token_savings.research_cache.clear()


def test_opt_in_cache_reuse_and_revision_invalidation(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    recorded = []
    async def answer(history, model, provider, fallback):
        recorded.append(history)
        return {"content": f"answer {len(recorded)}", "provider": "ollama", "model": "synthetic-model"}
    monkeypatch.setattr(providers, "chat", answer)
    doc = storage.create_document("Moon observations", "The moon has bright ridges and craters.")
    request = {"question": "How are moon craters observed?", "provider": "ollama",
               "local_answer_cache": True}
    one = client.post("/api/v1/research/answer", headers=H, json=request)
    two = client.post("/api/v1/research/answer", headers=H, json=request)
    assert one.status_code == two.status_code == 200
    assert one.json()["cache"]["hit"] is False
    assert two.json()["cache"]["hit"] is True
    assert two.json()["sent_to_cloud"] is False
    assert two.json()["answer"] == one.json()["answer"] == "answer 1"
    assert len(recorded) == 1
    assert [item["id"] for item in two.json()["sources"]] == [doc["id"]]
    assert client.get("/api/v1/cache/status", headers=H).json()["research"]["entries"] == 1

    # Updating the document with same excerpt words still invalidates its answer.
    changed = storage.update_document(doc["id"], "Moon observations",
                                      "The moon has bright ridges and impact craters.")
    assert changed is not None
    after_edit = client.post("/api/v1/research/answer", headers=H, json=request)
    assert after_edit.json()["cache"]["hit"] is False
    assert after_edit.json()["answer"] == "answer 2"
    assert len(recorded) == 2

    assert storage.delete_document(doc["id"])
    deleted = client.post("/api/v1/research/answer", headers=H, json=request)
    assert deleted.status_code == 200
    assert deleted.json()["provider"] == "none"
    assert deleted.json()["sources"] == []
    assert len(recorded) == 2


def test_research_cache_is_never_automatic_and_rejects_no_auth(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    record = []
    async def answer(*_args):
        record.append(1)
        return {"content": "synthetic response", "provider": "ollama", "model": "local"}
    monkeypatch.setattr(providers, "chat", answer)
    storage.create_document("Seaside", "Seaside sunsets gleam with crimson clouds.")
    for _ in range(2):
        resp = client.post("/api/v1/research/answer", headers=H,
                           json={"question": "Describe seaside sunsets", "provider": "ollama"})
        assert resp.status_code == 200 and "cache" not in resp.json()
    assert len(record) == 2
    assert client.post("/api/v1/research/answer", json={
        "question": "Describe seaside sunsets", "provider": "ollama",
        "local_answer_cache": True,
    }).status_code == 401


def test_research_cached_cloud_call_preserves_auth_and_admission(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-key")
    events = []
    async def budget():
        events.append("budget")
    def admitted(kind, approved):
        assert kind == "research" and approved
        events.append("admitted")
    async def answer(*_args):
        events.append("provider")
        return {"content": "synthetic-cloud-answer", "provider": "openrouter", "model": "demo"}
    monkeypatch.setattr(providers, "verify_cloud_key_budget", budget)
    monkeypatch.setattr(storage, "admit_cloud_call", admitted)
    monkeypatch.setattr(providers, "chat", answer)
    storage.create_document("Maritime", "Maritime fleets chart coastal routes.")
    request = {"question": "Which maritime fleets?", "provider": "openrouter",
               "allow_cloud_processing": True, "local_answer_cache": True}
    assert client.post("/api/v1/research/answer", headers=H, json=request).json()["cache"]["hit"] is False
    cached = client.post("/api/v1/research/answer", headers=H, json=request).json()
    assert cached["cache"]["hit"] is True
    assert cached["sent_to_cloud"] is False
    assert cached["original_provider"] == "openrouter"
    assert events == ["budget", "admitted", "provider"]
    denied = {**request, "allow_cloud_processing": False}
    assert client.post("/api/v1/research/answer", headers=H, json=denied).status_code == 403
    assert events == ["budget", "admitted", "provider"]


def test_clearing_explicitly_purges_research_and_chat_entries(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    storage.create_document("Forest", "Forest canopy covers the valley.")
    async def answer(*_args):
        return {"provider": "ollama", "model": "local", "content": "answer"}
    monkeypatch.setattr(providers, "chat", answer)
    result = client.post("/api/v1/research/answer", headers=H, json={
        "question": "What is a forest canopy?", "provider": "ollama",
        "local_answer_cache": True,
    })
    assert result.status_code == 200
    assert client.post("/api/v1/cache/clear", headers=H, json={}).status_code == 403
    cleared = client.post("/api/v1/cache/clear", headers=H, json={"approved": True})
    assert cleared.status_code == 200
    assert cleared.json()["research_cleared"] == 1
    assert client.get("/api/v1/cache/status", headers=H).json()["research"]["entries"] == 0


def test_research_versioned_cache_survives_unrelated_updates_only_when_sources_unchanged(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    calls = []
    async def answer(*_args):
        calls.append(1)
        return {"provider": "ollama", "model": "local", "content": "reply"}
    monkeypatch.setattr(providers, "chat", answer)
    original = storage.create_document("Volcano", "Volcano magma flows along lava tubes.")
    question = {"question": "Volcano magma flows?", "provider": "ollama",
                "local_answer_cache": True}
    assert client.post("/api/v1/research/answer", headers=H, json=question).status_code == 200
    unrelated = storage.create_document("Orchard", "Orchard blossoms signal spring.")
    assert client.post("/api/v1/research/answer", headers=H, json=question).json()["cache"]["hit"]
    assert len(calls) == 1
    storage.update_document(unrelated["id"], "Orchard", "Spring blossoms in orchard.")
    assert client.post("/api/v1/research/answer", headers=H, json=question).json()["cache"]["hit"]
    storage.delete_document(original["id"])
    assert client.post("/api/v1/research/answer", headers=H, json=question).json()["provider"] == "none"
