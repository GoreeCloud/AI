"""Content-free cloud approval admission receipts and explicit user erasure."""
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import storage
from app.main import app

HEADERS = {"Authorization": "Bearer test-owner-token"}
client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_privacy_db(tmp_path, monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "test-owner-token")
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(tmp_path / "privacy.sqlite3"))
    monkeypatch.setenv("GOREECLOUD_AI_DAILY_CLOUD_REQUEST_LIMIT", "20")
    monkeypatch.setenv("GOREECLOUD_AI_CONSENT_RECEIPT_RETENTION_DAYS", "30")


def test_no_approval_rejected_without_charging_quota():
    with pytest.raises(HTTPException) as exc:
        storage.admit_cloud_call("chat")
    assert exc.value.status_code == 403
    assert storage.cloud_quota()["admitted"] == 0
    assert storage.list_cloud_consent_receipts()["receipts"] == []


def test_admission_records_no_content_or_keys(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-test-provider-key")
    receipt_kinds = [
        ("chat", "cloud-processing-consent"),
        ("chat-stream", "cloud-processing-consent"),
        ("image", "paid-image-approval"),
        ("agent-plan", "cloud-processing-consent"),
        ("research", "cloud-processing-consent"),
    ]
    for kind, _approval in receipt_kinds:
        storage.admit_cloud_call(kind, approved=True)
    receipts = storage.list_cloud_consent_receipts()["receipts"]
    assert len(receipts) == 5
    assert {r["kind"]: r["approval"] for r in receipts} == dict(receipt_kinds)
    serialized = str(receipts)
    assert "synthetic-test-provider-key" not in serialized
    assert "Authorization" not in serialized
    assert "message" not in serialized.lower()
    assert all(len(r["id"]) == 36 for r in receipts)
    assert storage.cloud_quota()["admitted"] == 5


def test_unknown_kind_and_invalid_retention_fail_closed(monkeypatch):
    with pytest.raises(HTTPException) as e:
        storage.admit_cloud_call("unapproved-tool", approved=True)
    assert e.value.status_code == 422
    monkeypatch.setenv("GOREECLOUD_AI_CONSENT_RECEIPT_RETENTION_DAYS", "-1")
    with pytest.raises(HTTPException) as e:
        storage.admit_cloud_call("chat", approved=True)
    assert e.value.status_code == 503
    assert storage.cloud_quota()["admitted"] == 0


def test_receipt_quota_atomic_with_concurrent_cloud_admissions(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_DAILY_CLOUD_REQUEST_LIMIT", "2")
    def attempt(_):
        try:
            storage.admit_cloud_call("research", approved=True)
            return True
        except HTTPException as exc:
            assert exc.status_code == 429
            return False
    with ThreadPoolExecutor(max_workers=7) as pool:
        results = list(pool.map(attempt, range(7)))
    assert sum(results) == 2
    assert len(storage.list_cloud_consent_receipts()["receipts"]) == 2
    assert storage.cloud_quota()["admitted"] == 2


def test_retention_and_explicit_clear_keeps_quota():
    storage.admit_cloud_call("chat", approved=True)
    old = (datetime.now(UTC) - timedelta(days=40)).isoformat()
    with storage._connection() as db:
        db.execute("UPDATE cloud_consent_receipts SET created_at = ?", (old,))
    assert storage.list_cloud_consent_receipts()["receipts"] == []
    storage.admit_cloud_call("image", approved=True)
    assert client.get("/api/v1/privacy/consent-receipts").status_code == 401
    response = client.get("/api/v1/privacy/consent-receipts", headers=HEADERS)
    assert response.status_code == 200
    assert len(response.json()["receipts"]) == 1
    assert client.post("/api/v1/privacy/consent-receipts/clear",
                       headers=HEADERS, json={"approved": False}).status_code == 403
    assert client.get("/api/v1/privacy/consent-receipts",
                      headers=HEADERS).json()["receipts"]
    result = client.post("/api/v1/privacy/consent-receipts/clear",
                         headers=HEADERS, json={"approved": True})
    assert result.status_code == 200
    assert result.json()["deleted_receipts"] == 1
    assert storage.list_cloud_consent_receipts()["receipts"] == []
    assert storage.cloud_quota()["admitted"] == 2


def test_cloud_chat_without_consent_cannot_create_receipt(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-only")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    response = client.post("/api/v1/chat", headers=HEADERS, json={
        "provider": "openrouter", "messages": [{"role": "user", "content": "private"}],
    })
    assert response.status_code == 403
    assert storage.list_cloud_consent_receipts()["receipts"] == []
    assert storage.cloud_quota()["admitted"] == 0
