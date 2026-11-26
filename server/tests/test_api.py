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


@pytest.mark.parametrize("prefix", ["", "/preview"])
def test_chat_validation_does_not_echo_prompt(monkeypatch, prefix):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    prompt = "synthetic private conversation text"
    with TestClient(app, root_path=prefix) as routed_client:
        response = routed_client.post(f"{prefix}/api/v1/chat", headers=HEADERS, json={
            "messages": [{"role": "user", "content": prompt}],
            "context_mode": "budget",
        })

    assert response.status_code == 422
    assert prompt not in response.text
    assert response.headers["cache-control"] == "no-store"
    error, = response.json()["detail"]
    assert set(error) == {"type", "loc", "msg"}
    assert error["type"] == "value_error"
    assert error["loc"] == ["body"]
    assert "declared model context window" in error["msg"]


def test_document_validation_preserves_field_without_echoing_input(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    document_text = "synthetic private document text"
    response = client.post("/api/v1/documents", headers=HEADERS, json={
        "title": "Synthetic draft",
        "body": {"text": document_text},
    })

    assert response.status_code == 422
    assert document_text not in response.text
    assert response.json() == {"detail": [{
        "type": "string_type",
        "loc": ["body", "body"],
        "msg": "Input should be a valid string",
    }]}
