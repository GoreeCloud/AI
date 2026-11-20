import os

import pytest

os.environ["GOREECLOUD_AI_TOKEN"] = "test-owner-token"

from fastapi.testclient import TestClient

from app.main import app, checked_reference

client = TestClient(app)
HEADERS = {"Authorization": "Bearer test-owner-token"}


def test_health_public():
    assert client.get("/api/health").json()["status"] == "ok"


def test_protected():
    assert client.get("/api/v1/documents").status_code == 401
    assert client.get("/api/v1/documents", headers=HEADERS).status_code == 200


def test_document_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(tmp_path / "docs.sqlite"))
    created = client.post("/api/v1/documents",
                          headers=HEADERS, json={"title": "Test", "body": "# Safe"} )
    assert created.status_code == 201
    doc_id = created.json()["id"]
    assert client.get(f"/api/v1/documents/{doc_id}", headers=HEADERS).json()["body"] == "# Safe"
    revised = client.put(f"/api/v1/documents/{doc_id}", headers=HEADERS,
                         json={"title": "Test revised", "body": "Content"})
    assert revised.status_code == 200
    assert client.get(f"/api/v1/documents/{doc_id}/export?format=md", headers=HEADERS).content == b"Content"
    assert client.get(f"/api/v1/documents/{doc_id}/export?format=docx", headers=HEADERS).status_code == 200


def test_paid_image_gate():
    r = client.post("/api/v1/images", headers=HEADERS,
                    json={"prompt": "sunrise on a snowy mountain"})
    assert r.status_code == 403


def test_mcp_manual_gate():
    r = client.post("/api/v1/mcp/call", headers=HEADERS,
                    json={"name": "file_delete", "arguments": {}})
    assert r.status_code == 403


def test_agent_gate():
    r = client.post("/api/v1/agents/run", headers=HEADERS, json={
        "action": "document.read",
        "document_id": "3c8d8d41-5a44-4831-8cc0-7caeb05729ae"
    })
    assert r.status_code == 403


def test_reference_validation():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as captured:
        checked_reference("https://remote.site/example.png")
    assert captured.value.status_code == 422


def test_chat_validation():
    r = client.post("/api/v1/chat", headers=HEADERS, json={
        "messages": [{"role": "user", "content": ""}]
    })
    assert r.status_code == 422
