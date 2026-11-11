from fastapi.testclient import TestClient

from goreecloud_ai.app import create_app
from goreecloud_ai.settings import Settings


class FakeOllama:
    async def models(self):
        return []


def client(tmp_path, token=None):
    return TestClient(create_app(
        Settings(database_path=str(tmp_path / "security.sqlite"), api_token=token),
        FakeOllama(),
    ))


def test_local_ui_uses_same_origin_csp_and_frame_restrictions(tmp_path):
    response = client(tmp_path).get("/")
    assert response.status_code == 200
    policy = response.headers["content-security-policy"]
    assert "script-src 'self'" in policy
    assert "connect-src 'self'" in policy
    assert "frame-ancestors 'none'" in policy
    assert "object-src 'none'" in policy
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_sensitive_api_responses_cannot_be_cached(tmp_path):
    c = client(tmp_path)
    chat = c.post("/api/chats", json={}).json()
    for path in ("/api/chats", "/api/chats/" + chat["id"], "/api/chats/" + chat["id"] + "/export",
                 "/api/knowledge/documents", "/api/health"):
        response = c.get(path)
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["pragma"] == "no-cache"


def test_unauthorized_api_error_not_cachable(tmp_path):
    c = client(tmp_path, token="test-token-1234567890")
    response = c.get("/api/chats")
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_static_script_uses_headers_without_forcing_api_cache_policy(tmp_path):
    response = client(tmp_path).get("/assets/app.js")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert response.headers.get("cache-control") != "no-store"
