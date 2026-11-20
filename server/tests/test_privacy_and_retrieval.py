"""Privacy, storage lifecycle, retrieval, quota and server-side authorization tests."""
import os

import pytest
from fastapi.testclient import TestClient

os.environ["GOREECLOUD_AI_TOKEN"] = "test-owner-token"

from app import providers, storage  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
HEADERS = {"Authorization": "Bearer test-owner-token"}


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(tmp_path / "ai.sqlite3"))
    monkeypatch.setenv("GOREECLOUD_AI_DAILY_CLOUD_REQUEST_LIMIT", "2")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)


def test_document_search_update_delete_and_private_permissions(tmp_path):
    created = client.post("/api/v1/documents", headers=HEADERS,
                          json={"title": "Aurora Guide", "body": "Watch luminous aurora tonight"}).json()
    search = client.get("/api/v1/search/documents?q=aurora", headers=HEADERS)
    assert search.status_code == 200
    assert [hit["id"] for hit in search.json()["results"]] == [created["id"]]
    assert client.get("/api/v1/search/documents?q=aurora").status_code == 401

    update = client.put("/api/v1/documents/" + created["id"], headers=HEADERS,
                        json={"title": "New title", "body": "Completely different lunar subject"})
    assert update.status_code == 200
    assert client.get("/api/v1/search/documents?q=aurora", headers=HEADERS).json()["results"] == []
    assert client.get("/api/v1/search/documents?q=lunar", headers=HEADERS).json()["results"][0]["id"] == created["id"]
    assert client.delete("/api/v1/documents/" + created["id"], headers=HEADERS).status_code == 204
    assert client.get("/api/v1/search/documents?q=lunar", headers=HEADERS).json()["results"] == []
    assert client.delete("/api/v1/documents/" + created["id"], headers=HEADERS).status_code == 404
    dbfile = tmp_path / "ai.sqlite3"
    assert dbfile.stat().st_mode & 0o077 == 0


def test_explicit_saved_conversation_and_deletion():
    assert client.get("/api/v1/conversations", headers=HEADERS).json() == []
    item = client.post("/api/v1/conversations", headers=HEADERS,
                       json={"title": "Private chat", "messages": [
                           {"role": "user", "content": "Hi"},
                           {"role": "assistant", "content": "Hello"}]})
    assert item.status_code == 201
    conversation_id = item.json()["id"]
    assert len(item.json()["messages"]) == 2
    assert client.get("/api/v1/conversations", headers=HEADERS).json()[0]["message_count"] == 2
    assert client.get("/api/v1/conversations/" + conversation_id).status_code == 401
    assert client.delete("/api/v1/conversations/" + conversation_id, headers=HEADERS).status_code == 204
    assert client.get("/api/v1/conversations/" + conversation_id, headers=HEADERS).status_code == 404


def test_no_cloud_without_consent(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-provider-key")
    response = client.post("/api/v1/chat", headers=HEADERS,
                           json={"messages": [{"role": "user", "content": "Hi"}]})
    assert response.status_code == 403
    assert storage.cloud_quota()["admitted"] == 0


def test_auto_prefers_local_without_cloud_consent(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-provider-key")
    monkeypatch.setenv("OLLAMA_MODEL", "local-model")

    async def fake_chat(messages, model, provider, fallback):
        assert provider == "ollama"
        return {"provider": "ollama", "model": "local-model", "content": "Local", "usage": {}}

    monkeypatch.setattr(providers, "chat", fake_chat)
    result = client.post("/api/v1/chat", headers=HEADERS,
                         json={"messages": [{"role": "user", "content": "Hi"}]})
    assert result.status_code == 200
    assert result.json()["content"] == "Local"
    assert storage.cloud_quota()["admitted"] == 0


def test_cloud_consent_and_quota_are_enforced(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-provider-key")

    async def fake_chat(messages, model, provider, fallback):
        assert provider == "openrouter"
        return {"provider": "openrouter", "model": "mock", "content": "Hello", "usage": {}}

    monkeypatch.setattr(providers, "chat", fake_chat)
    body = {"messages": [{"role": "user", "content": "Hi"}],
            "allow_cloud_processing": True}
    assert client.post("/api/v1/chat", headers=HEADERS, json=body).status_code == 200
    assert client.post("/api/v1/chat", headers=HEADERS, json=body).status_code == 200
    assert client.post("/api/v1/chat", headers=HEADERS, json=body).status_code == 429
    assert client.get("/api/v1/quotas", headers=HEADERS).json()["remaining"] == 0


def test_streamed_chat_enforces_consent_and_emits_events(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-provider-key")

    async def fake_stream(messages, model, provider):
        assert provider == "openrouter"
        yield {"type": "delta", "content": "Goree"}
        yield {"type": "done", "provider": "openrouter", "model": "mock-model"}

    monkeypatch.setattr(providers, "stream_chat", fake_stream)
    body = {"messages": [{"role": "user", "content": "Hi"}]}
    assert client.post("/api/v1/chat/stream", headers=HEADERS, json=body).status_code == 403
    body["allow_cloud_processing"] = True
    answer = client.post("/api/v1/chat/stream", headers=HEADERS, json=body)
    assert answer.status_code == 200
    assert '"type": "delta"' in answer.text
    assert '"type": "done"' in answer.text
    assert storage.cloud_quota()["admitted"] == 1


def test_retrieval_empty_response_never_transmits_to_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-provider-key")
    r = client.post("/api/v1/research/answer", headers=HEADERS,
                    json={"question": "Where is a telescope?"})
    assert r.status_code == 200
    assert r.json()["sources"] == []
    assert r.json()["provider"] == "none"
    assert storage.cloud_quota()["admitted"] == 0


def test_retrieval_requires_consent_before_external_excerpts(monkeypatch):
    created = client.post("/api/v1/documents", headers=HEADERS,
                          json={"title": "Private Observatory", "body": "A telescope stands on a hill."}).json()
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-provider-key")

    async def fake_chat(messages, model, provider, fallback):
        assert provider == "openrouter"
        assert created["id"] in messages[1]["content"]
        return {"provider": "openrouter", "model": "mock", "content": "Cited.", "usage": {}}

    monkeypatch.setattr(providers, "chat", fake_chat)
    payload = {"question": "Where is the telescope?"}
    assert client.post("/api/v1/research/answer", headers=HEADERS, json=payload).status_code == 403
    payload["allow_cloud_processing"] = True
    answer = client.post("/api/v1/research/answer", headers=HEADERS, json=payload)
    assert answer.status_code == 200
    assert answer.json()["sources"][0]["id"] == created["id"]
    assert answer.json()["sent_to_cloud"] is True


def test_bad_input_and_invalid_saved_roles():
    assert client.post("/api/v1/conversations", headers=HEADERS, json={
        "title": "bad", "messages": [{"role": "system", "content": "Not permitted"}]}).status_code == 422
    assert client.get("/api/v1/search/documents?q=%22%20OR%20%2A", headers=HEADERS).status_code == 200
    assert client.get("/api/v1/privacy/status", headers=HEADERS).json()["identity_integrated"] is False


def test_stream_rejects_implicit_fallback(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-provider-key")
    result = client.post("/api/v1/chat/stream", headers=HEADERS,
                         json={"messages": [{"role": "user", "content": "Hello"}],
                               "allow_cloud_processing": True, "allow_local_fallback": True})
    assert result.status_code == 422
    assert storage.cloud_quota()["admitted"] == 0


def test_privacy_headers_and_search_injection():
    response = client.get("/api/v1/quotas", headers=HEADERS)
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    payload = {"title": "A policy", "body": "Please do not leak documents"}
    assert client.post("/api/v1/documents", headers=HEADERS, json=payload).status_code == 201
    query = 'pol" OR content:*'
    response = client.get("/api/v1/search/documents", headers=HEADERS, params={"q": query})
    assert response.status_code == 200


def test_document_parser_rejects_zip_bomb_metadata():
    import io
    import zipfile

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("word/document.xml", b"A" * 25_000_001)
    response = client.post("/api/v1/documents/extract", headers=HEADERS,
                           files={"file": ("huge.docx", output.getvalue(),
                                           "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert response.status_code == 413


def test_existing_preindex_documents_are_migrated(tmp_path, monkeypatch):
    import sqlite3
    from uuid import uuid4

    path = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE documents (id TEXT PRIMARY KEY, title TEXT NOT NULL, "
                   "body TEXT NOT NULL, updated_at TEXT NOT NULL)")
        db.execute("INSERT INTO documents VALUES (?, ?, ?, ?)",
                   (str(uuid4()), "Migration record", "Unique silver comet information", "2026-11-20"))
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(path))
    hits = storage.search_documents("silver comet")
    assert len(hits) == 1
    assert hits[0]["title"] == "Migration record"


def test_atomic_cloud_quota_under_parallel_requests(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor

    from fastapi import HTTPException

    monkeypatch.setenv("GOREECLOUD_AI_DAILY_CLOUD_REQUEST_LIMIT", "2")

    def attempt():
        try:
            storage.admit_cloud_call("chat")
            return True
        except HTTPException as exc:
            assert exc.status_code == 429
            return False

    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda _: attempt(), range(6)))
    assert sum(results) == 2
    assert storage.cloud_quota()["admitted"] == 2
