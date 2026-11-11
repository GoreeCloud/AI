import sqlite3

import pytest
from fastapi.testclient import TestClient

from goreecloud_ai.app import create_app
from goreecloud_ai.knowledge import KnowledgeStore
from goreecloud_ai.semantic import SemanticIndex, cosine
from goreecloud_ai.settings import Settings


MODEL = "embeddinggemma:latest"


class FakeEmbeddedOllama:
    def __init__(self):
        self.embed_calls = 0
        self.chat_calls = []

    async def models(self):
        return ["gemma3:4b", MODEL]

    async def embed(self, model, inputs):
        assert model == MODEL
        self.embed_calls += 1
        return [[1.0, 0.0] for _ in inputs]

    async def chat(self, model, messages):
        self.chat_calls.append(messages)
        return "From indexed knowledge"

    async def stream_chat(self, model, messages):
        self.chat_calls.append(messages)
        yield "From indexed knowledge"


def setup_client(tmp_path, token=None):
    backend = FakeEmbeddedOllama()
    app = create_app(Settings(database_path=str(tmp_path / "ai.sqlite"), api_token=token), backend)
    return TestClient(app), backend


def test_semantic_status_and_missing_index_preflight(tmp_path):
    client, backend = setup_client(tmp_path)
    assert client.get("/api/knowledge/semantic/status").json() == []
    missing = client.post("/api/knowledge/semantic/search", json={"query": "cats", "model": MODEL})
    assert missing.status_code == 409
    assert backend.embed_calls == 0
    chat = client.post("/api/chats", json={}).json()
    grounded = client.post("/api/chats/" + chat["id"] + "/messages", json={
        "content": "cats", "use_knowledge": True, "knowledge_mode": "semantic", "embedding_model": MODEL
    })
    assert grounded.status_code == 409
    assert backend.embed_calls == 0
    assert backend.chat_calls == []
    assert client.get("/api/chats/" + chat["id"]).json()["messages"] == []


def test_semantic_status_index_search_and_delete(tmp_path):
    client, backend = setup_client(tmp_path)
    document = client.post("/api/knowledge/documents", json={
        "title": "Cats", "content": "Cats have whiskers."
    }).json()
    indexed = client.post("/api/knowledge/semantic/index", json={
        "document_id": document["id"], "model": MODEL
    })
    assert indexed.status_code == 200
    assert indexed.json()["chunks"] == 1
    assert client.get("/api/knowledge/semantic/status").json() == [
        {"model": MODEL, "chunks": 1, "documents": 1}
    ]
    result = client.post("/api/knowledge/semantic/search", json={
        "query": "feline traits", "model": MODEL
    })
    assert result.status_code == 200
    assert result.json()[0]["id"] == document["id"]
    assert result.json()[0]["retrieval"] == "semantic"
    assert backend.embed_calls == 2
    assert client.delete("/api/knowledge/documents/" + document["id"]).status_code == 200
    assert client.get("/api/knowledge/semantic/status").json() == []


def test_semantic_status_requires_shared_token_when_configured(tmp_path):
    client, _ = setup_client(tmp_path, token="test-token-1234567890")
    assert client.get("/api/knowledge/semantic/status").status_code == 401
    ok = client.get("/api/knowledge/semantic/status", headers={"X-API-Key": "test-token-1234567890"})
    assert ok.status_code == 200


def test_semantic_scan_refuses_partial_results(tmp_path, monkeypatch):
    from goreecloud_ai import semantic
    path = str(tmp_path / "cap.sqlite")
    store = KnowledgeStore(path)
    index = SemanticIndex(path)
    document = store.add("Whole document", "Content of three chunks")
    index.save(document["id"], MODEL, ["part A", "part B", "part C"],
               [[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]])
    monkeypatch.setattr(semantic, "MAX_SEARCH_CHUNKS", 2)
    with pytest.raises(ValueError, match="capacity"):
        index.search([1.0, 0.0], MODEL)


def test_corrupt_index_and_model_dimensions_fail_closed(tmp_path):
    path = str(tmp_path / "corrupt.sqlite")
    store = KnowledgeStore(path)
    index = SemanticIndex(path)
    document = store.add("Corruption", "Retain a detectable index failure")
    index.save(document["id"], MODEL, ["chunk"], [[1.0, 0.0]])
    with pytest.raises(ValueError, match="dimensions"):
        index.search([1.0, 0.0, 0.0], MODEL)
    with sqlite3.connect(path) as db:
        db.execute("UPDATE semantic_chunks SET vector_json='not-json' WHERE document_id=?", (document["id"],))
    with pytest.raises(ValueError, match="corrupt"):
        index.search([1.0, 0.0], MODEL)


def test_large_finite_vectors_do_not_overflow_cosine():
    assert cosine([1e308, 0.0], [1e308, 0.0]) == pytest.approx(1.0)
    assert cosine([1e308, 0.0], [0.0, 1e308]) == pytest.approx(0.0)


def test_no_semantic_failure_persists_a_chat_exchange(tmp_path):
    client, backend = setup_client(tmp_path)
    doc = client.post("/api/knowledge/documents", json={"title": "Reference", "content": "Cats have whiskers."}).json()
    assert client.post("/api/knowledge/semantic/index", json={"document_id": doc["id"], "model": MODEL}).status_code == 200
    chat = client.post("/api/chats", json={}).json()
    # Modify the saved embedding to simulate a model change; the API must reject it.
    with sqlite3.connect(str(tmp_path / "ai.sqlite")) as db:
        db.execute("UPDATE semantic_chunks SET vector_json='[0.0,1.0,0.0]' WHERE document_id=?", (doc["id"],))
    result = client.post("/api/chats/" + chat["id"] + "/stream", json={
        "content": "Describe cats", "use_knowledge": True, "knowledge_mode": "semantic", "embedding_model": MODEL
    })
    assert result.status_code == 422
    assert backend.chat_calls == []
    assert client.get("/api/chats/" + chat["id"]).json()["messages"] == []
