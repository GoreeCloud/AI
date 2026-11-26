"""Synthetic-only malformed authentication and configuration regression tests."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def owner(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "synthetic-owner-token")


@pytest.mark.parametrize("token", [b"wrong", b"\xff", b"synthetic-\xe9"])
def test_malformed_bearer_is_unauthorized(token):
    response = client.get("/api/v1/models",
                          headers=[(b"authorization", b"Bearer " + token)])
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    assert response.json() == {"detail": "Invalid authentication credentials"}


def test_valid_ascii_owner_token_still_works():
    response = client.get("/api/v1/models", headers={
        "Authorization": "Bearer synthetic-owner-token",
    })
    assert response.status_code == 200


def test_invalid_non_ascii_config_fails_closed(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "synthetic-\u00e9")
    response = client.get("/api/v1/models", headers={
        "Authorization": "Bearer synthetic-owner-token",
    })
    assert response.status_code == 503
    assert response.json() == {"detail": "Owner API token configuration is invalid"}


def test_malformed_oidc_issuer_returns_configuration_error(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "oidc")
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_ISSUER", "https://[invalid")
    response = client.get("/api/v1/models", headers={
        "Authorization": "Bearer synthetic-owner-token",
    })
    assert response.status_code == 503
    assert "invalid" not in response.text
