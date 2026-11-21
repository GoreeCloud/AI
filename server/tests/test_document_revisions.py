"""Opt-in document revisions with bounded retention and approved restore.

Synthetic records only; no providers, deployment or personal documents.
"""
import sqlite3

from fastapi.testclient import TestClient

from app import storage
from app.main import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer test-owner-token"}


def _create():
    response = client.post(
        "/api/v1/documents", headers=HEADERS, json={"title": "One", "body": "original"}
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_revision_opt_in_and_restore(tmp_path, monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "test-owner-token")
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(tmp_path / "history.db"))
    document_id = _create()
    url = f"/api/v1/documents/{document_id}"
    history = url + "/revisions"

    assert client.get(history).status_code == 401
    assert client.get(history, headers=HEADERS).json()["revisions"] == []
    assert client.put(url, headers=HEADERS, json={"title": "Two", "body": "no history"}).status_code == 200
    assert client.get(history, headers=HEADERS).json()["revisions"] == []
    assert client.put(url, headers=HEADERS, json={
        "title": "Three", "body": "latest", "record_revision": True
    }).status_code == 200
    records = client.get(history, headers=HEADERS).json()["revisions"]
    assert len(records) == 1
    assert records[0]["title"] == "Two"
    assert records[0]["body_characters"] == len("no history")
    revision_id = records[0]["id"]
    detail = history + "/" + revision_id
    assert client.get(detail, headers=HEADERS).json()["body"] == "no history"
    assert client.get(detail).status_code == 401
    assert client.get(history + "/" + document_id, headers=HEADERS).status_code == 404

    # Unchanged saves must not duplicate history; explicit false remains zero-copy.
    assert client.put(url, headers=HEADERS, json={
        "title": "Three", "body": "latest", "record_revision": True
    }).status_code == 200
    assert len(client.get(history, headers=HEADERS).json()["revisions"]) == 1
    assert client.post(detail + "/restore", headers=HEADERS, json={}).status_code == 403
    assert client.post(detail + "/restore", json={"approved": True}).status_code == 401
    assert client.get(url, headers=HEADERS).json()["body"] == "latest"

    restored = client.post(detail + "/restore", headers=HEADERS, json={"approved": True})
    assert restored.status_code == 200
    assert restored.json()["body"] == "no history"
    undo = client.get(history, headers=HEADERS).json()["revisions"]
    assert len(undo) == 2
    assert {r["title"] for r in undo} == {"Two", "Three"}
    assert client.post(detail + "/restore", headers=HEADERS,
                       json={"approved": True}).status_code == 200
    assert len(client.get(history, headers=HEADERS).json()["revisions"]) == 2


def test_bounded_20_versions_and_cascade_delete(tmp_path, monkeypatch):
    path = tmp_path / "bounded.sqlite3"
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(path))
    document_id = _create()
    for index in range(27):
        item = storage.update_document(
            document_id, "Document", f"Version {index}", record_revision=True
        )
        assert item["body"] == f"Version {index}"
    revisions = storage.list_document_revisions(document_id)
    assert len(revisions) == 20
    assert all("body" not in row for row in revisions)
    newest = storage.get_document_revision(document_id, revisions[0]["id"])
    assert newest["body"] == "Version 25"
    # First revision has been pruned and cannot be restored.
    assert all(rev["title"] == "Document" for rev in revisions)
    assert storage.get_document_revision(document_id, "missing") is None
    assert storage.delete_document(document_id)
    assert storage.list_document_revisions(document_id) is None
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM document_revisions").fetchone()[0] == 0


def test_strict_scoped_restore_requires_write(tmp_path, monkeypatch):
    """Route classification includes the new history operations for OIDC mode."""
    from app import security
    assert security._ROUTE_CAPABILITIES[(
        "GET", "/api/v1/documents/{document_id}/revisions"
    )] == "read"
    assert security._ROUTE_CAPABILITIES[(
        "GET", "/api/v1/documents/{document_id}/revisions/{revision_id}"
    )] == "read"
    assert security._ROUTE_CAPABILITIES[(
        "POST", "/api/v1/documents/{document_id}/revisions/{revision_id}/restore"
    )] == "write"
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(tmp_path / "missing.db"))
    doc = "e34ac52a-27a3-4c6f-988a-55b79e71451c"
    rev = "be3ac52a-27a3-4c6f-988a-55b79e71451c"
    assert client.get(f"/api/v1/documents/{doc}/revisions", headers=HEADERS).status_code == 404
    assert client.post(f"/api/v1/documents/{doc}/revisions/{rev}/restore",
                       headers=HEADERS, json={"approved": True}).status_code == 404
