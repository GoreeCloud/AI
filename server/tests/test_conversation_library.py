"""Local saved conversation library regression tests; synthetic data only."""
import sqlite3

from fastapi.testclient import TestClient

from app import storage
from app.main import app

client = TestClient(app)
HEADERS = {"Authorization": "Bearer test-owner-token"}


def test_search_rename_export_and_delete(tmp_path, monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "test-owner-token")
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(tmp_path / "conversation.sqlite3"))

    created = client.post("/api/v1/conversations", headers=HEADERS, json={
        "title": "First discussion", "messages": [
            {"role": "user", "content": "Saffron aurora dances tonight"},
            {"role": "assistant", "content": "Understood — look for saffron sky"},
        ],
    })
    assert created.status_code == 201
    conversation_id = created.json()["id"]

    assert client.get("/api/v1/search/conversations?q=Saffron").status_code == 401
    search = client.get("/api/v1/search/conversations?q=aurora", headers=HEADERS)
    assert search.status_code == 200
    assert [row["id"] for row in search.json()["results"]] == [conversation_id]
    assert search.json()["results"][0]["message_count"] == 2

    # No arbitrary user-provided FTS5 operators or SQL expressions are evaluated.
    for query in ("OR%20%22%20DROP", "%27%20OR%201%3D1", "%25_%5C", "%22%2A%22"):
        result = client.get("/api/v1/search/conversations?q=" + query, headers=HEADERS)
        assert result.status_code == 200
    assert client.get("/api/v1/search/conversations?q=x", headers=HEADERS).status_code == 422
    assert client.get("/api/v1/search/conversations?q=hello&limit=51",
                      headers=HEADERS).status_code == 422
    assert client.patch(f"/api/v1/conversations/{conversation_id}",
                        json={"title": "No auth"}).status_code == 401
    assert client.patch(f"/api/v1/conversations/{conversation_id}", headers=HEADERS,
                        json={"title": "   "}).status_code == 422

    renamed = client.patch(f"/api/v1/conversations/{conversation_id}", headers=HEADERS,
                           json={"title": "  Notes on astronomy  "})
    assert renamed.status_code == 200
    assert renamed.json()["title"] == "Notes on astronomy"
    assert renamed.json()["messages"][0]["content"] == "Saffron aurora dances tonight"
    assert client.get("/api/v1/search/conversations?q=astronomy",
                      headers=HEADERS).json()["results"][0]["id"] == conversation_id

    json_export = client.get(f"/api/v1/conversations/{conversation_id}/export?format=json",
                             headers=HEADERS)
    assert json_export.status_code == 200
    assert json_export.headers["cache-control"] == "no-store"
    assert json_export.headers["content-disposition"].startswith("attachment; filename=")
    body = json_export.json()
    assert client.post("/api/v1/conversations/import", json=body).status_code == 401
    imported = client.post("/api/v1/conversations/import", json=body, headers=HEADERS)
    assert imported.status_code == 201
    assert imported.json()['id'] != conversation_id
    assert imported.json()["messages"] == body["conversation"]["messages"]
    assert client.post("/api/v1/conversations/import", json={"schema": "unknown", "conversation": {}},
                       headers=HEADERS).status_code == 422
    assert body["schema"] == "goreecloud.ai.conversation.v1"
    assert body["conversation"]["messages"][0]["content"] == "Saffron aurora dances tonight"
    assert client.get(f"/api/v1/conversations/{conversation_id}/export").status_code == 401

    md_export = client.get(f"/api/v1/conversations/{conversation_id}/export?format=md",
                           headers=HEADERS)
    assert md_export.status_code == 200
    assert b"## You\n\nSaffron aurora" in md_export.content
    assert client.get(f"/api/v1/conversations/{conversation_id}/export?format=pdf",
                      headers=HEADERS).status_code == 422

    assert client.delete(f"/api/v1/conversations/{imported.json()['id']}",
                         headers=HEADERS).status_code == 204
    assert client.delete(f"/api/v1/conversations/{conversation_id}",
                         headers=HEADERS).status_code == 204
    assert client.get("/api/v1/search/conversations?q=Saffron",
                      headers=HEADERS).json()["results"] == []
    assert client.get(f"/api/v1/conversations/{conversation_id}/export",
                      headers=HEADERS).status_code == 404
    assert client.patch(f"/api/v1/conversations/{conversation_id}", headers=HEADERS,
                        json={"title": "missing"}).status_code == 404


def test_existing_sqlite_conversations_are_indexed(tmp_path, monkeypatch):
    """Upgrade existing opt-in snapshots without re-saving or migrating them."""
    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "plaintext")
    path = tmp_path / "older.sqlite3"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE conversations (id TEXT PRIMARY KEY, title TEXT NOT NULL,"
                   " created_at TEXT NOT NULL, updated_at TEXT NOT NULL)")
        db.execute("CREATE TABLE messages (id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,"
                   " role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL,"
                   " FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE)")
        db.execute("INSERT INTO conversations VALUES ('older', 'Archive', '2020', '2020')")
        db.execute("INSERT INTO messages VALUES ('first', 'older', 'user', 'Vermilion sailboat', '2020')")
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(path))
    assert storage.search_conversations("vermilion")[0]["id"] == "older"
    assert storage.search_conversations("Archive")[0]["id"] == "older"
    assert storage.search_conversations("xyznotfound") == []
    assert storage.delete_conversation("older")
    assert storage.search_conversations("vermilion") == []


def test_unicode_and_search_limits(tmp_path, monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(tmp_path / "unicode.sqlite3"))
    snapshot = storage.save_conversation("French notes", [
        {"role": "user", "content": "Météorite en orbite"}
    ])
    assert storage.search_conversations("Météorite")[0]["id"] == snapshot["id"]
    assert storage.search_conversations("!!") == []
