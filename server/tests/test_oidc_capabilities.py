"""Source-only signed-JWT capability authorization tests; no real Identity issuer."""
import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app import providers, security
from app.main import app

client = TestClient(app)


@pytest.fixture
def signed_access(tmp_path, monkeypatch):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    jwk.update({"kid": "mock-kid", "use": "sig", "alg": "RS256"})
    jwks = tmp_path / "public-keys.json"
    jwks.write_text(json.dumps({"keys": [jwk]}), encoding="utf-8")
    jwks.chmod(0o600)
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "oidc")
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_ENFORCE_CAPABILITY_SCOPES", "true")
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_ISSUER", "https://mock-id.example.test/goree")
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_AUDIENCE", "goreecloud-ai")
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_OWNER_SUB", "mock-owner")
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_REQUIRED_SCOPE", "goreecloud.ai.owner")
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_JWKS_PATH", str(jwks))
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(tmp_path / "data.sqlite3"))
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-only")
    def headers(*capabilities, root=True):
        now = datetime.now(UTC)
        scopes = [("goreecloud.ai." + c) for c in capabilities]
        if root:
            scopes.append("goreecloud.ai.owner")
        token = jwt.encode({
            "iss": "https://mock-id.example.test/goree", "aud": "goreecloud-ai",
            "sub": "mock-owner", "iat": now, "nbf": now,
            "exp": now + timedelta(minutes=5), "scope": " ".join(scopes),
        }, private, algorithm="RS256", headers={"kid": "mock-kid"})
        return {"Authorization": "Bearer " + token}
    return headers


def test_every_protected_route_is_classified():
    routes = {(method, route.path) for route in app.routes if isinstance(route, APIRoute)
              and route.path.startswith("/api/v1/") for method in route.methods}
    assert routes == set(security._ROUTE_CAPABILITIES)


def test_read_scope_cannot_write_or_infer(signed_access):
    read = signed_access("read")
    assert client.get("/api/v1/models", headers=read).status_code == 200
    assert client.get("/api/v1/privacy/status", headers=read).status_code == 200
    assert client.get("/api/v1/quotas", headers=read).status_code == 200
    assert client.post("/api/v1/documents", headers=read,
                       json={"title": "test", "body": "private"}).status_code == 403
    assert client.post("/api/v1/chat", headers=read, json={
        "provider": "ollama", "messages": [{"role": "user", "content": "hi"}],
    }).status_code == 403
    assert client.get("/api/v1/mcp/tools", headers=read).status_code == 403
    assert client.post("/api/v1/privacy/consent-receipts/clear", headers=read,
                       json={"approved": True}).status_code == 403
    assert client.get("/api/v1/documents", headers=signed_access("write")).status_code == 403
    assert client.get("/api/v1/models", headers=signed_access("read", root=False)).status_code == 401


def test_write_admin_and_tool_scopes_are_distinct(signed_access):
    writer = signed_access("write")
    created = client.post("/api/v1/documents", headers=writer,
                          json={"title": "sample", "body": "private"})
    assert created.status_code == 201
    doc_id = created.json()["id"]
    assert client.get(f"/api/v1/documents/{doc_id}", headers=writer).status_code == 403
    assert client.delete(f"/api/v1/documents/{doc_id}", headers=writer).status_code == 204
    assert client.post("/api/v1/privacy/consent-receipts/clear", headers=writer,
                       json={"approved": True}).status_code == 403
    assert client.post("/api/v1/privacy/consent-receipts/clear", headers=signed_access("admin"),
                       json={"approved": True}).status_code == 200
    tool_user = signed_access("tools")
    assert client.post("/api/v1/agents/run", headers=tool_user, json={
        "action": "document.read", "document_id": doc_id, "approved": True,
    }).status_code == 404


def test_cloud_scope_checked_only_on_cloud_route(signed_access, monkeypatch):
    async def fake_budget():
        return None
    async def fake_chat(*_args, **_kwargs):
        return {"content": "from synthetic cloud", "provider": "openrouter", "model": "mock"}
    monkeypatch.setattr(providers, "verify_cloud_key_budget", fake_budget)
    monkeypatch.setattr(providers, "chat", fake_chat)
    req = {"provider": "openrouter", "allow_cloud_processing": True,
           "messages": [{"role": "user", "content": "synthetic"}]}
    no_cloud = client.post("/api/v1/chat", headers=signed_access("inference"), json=req)
    assert no_cloud.status_code == 403
    yes_cloud = client.post("/api/v1/chat", headers=signed_access("inference", "cloud"), json=req)
    assert yes_cloud.status_code == 200
    assert yes_cloud.json()["content"] == "from synthetic cloud"
    assert client.post("/api/v1/images", headers=signed_access("paid"),
                       json={"prompt": "dummy image", "approve_paid_generation": True}).status_code == 403
    assert client.post("/api/v1/images", headers=signed_access("cloud"),
                       json={"prompt": "dummy image", "approve_paid_generation": True}).status_code == 403


def test_existing_oidc_mode_can_opt_out_of_new_capabilities(signed_access, monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_ENFORCE_CAPABILITY_SCOPES", "false")
    assert client.get("/api/v1/models", headers=signed_access()).status_code == 200
    assert client.get("/api/v1/conversations", headers=signed_access()).status_code == 200
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_ENFORCE_CAPABILITY_SCOPES", "yes")
    assert client.get("/api/v1/models", headers=signed_access()).status_code == 503


def test_local_owner_mode_remains_compatible(signed_access, monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "owner")
    monkeypatch.setenv("GOREECLOUD_AI_TOKEN", "synthetic-local-owner")
    heads = {"Authorization": "Bearer synthetic-local-owner"}
    assert client.get("/api/v1/models", headers=heads).status_code == 200
    assert client.post("/api/v1/conversations", headers=heads,
                       json={"title": "Local", "messages": [
                           {"role": "user", "content": "Local note"}]}).status_code == 201



def test_all_cloud_inference_paths_require_cloud_capability(signed_access, monkeypatch):
    from app import storage
    storage.create_document("Synthetic cloud reference", "A cerulean comet passed the station.")
    head = signed_access("inference")
    requests = [
        ("/api/v1/chat", {"provider": "openrouter",
                          "allow_cloud_processing": True,
                          "messages": [{"role": "user", "content": "hello"}]}),
        ("/api/v1/chat/stream", {"provider": "openrouter",
                                 "allow_cloud_processing": True,
                                 "messages": [{"role": "user", "content": "hello"}]}),
        ("/api/v1/agents/plan", {"provider": "openrouter",
                                 "allow_cloud_processing": True,
                                 "goal": "draft a synthetic checklist"}),
        ("/api/v1/research/answer", {"provider": "openrouter",
                                    "allow_cloud_processing": True,
                                    "question": "What cerulean comet passed?"}),
    ]
    for route, payload in requests:
        response = client.post(route, headers=head, json=payload)
        assert response.status_code == 403, route
    assert storage.cloud_quota()["admitted"] == 0


def test_local_inference_remains_authorized_without_cloud_scope(signed_access, monkeypatch):
    async def synthetic(*_args, **_kwargs):
        return {"provider": "ollama", "model": "local-fixture", "content": "local answer"}
    monkeypatch.setattr(providers, "chat", synthetic)
    response = client.post("/api/v1/chat", headers=signed_access("inference"), json={
        "provider": "ollama", "allow_cloud_processing": False,
        "messages": [{"role": "user", "content": "private example"}],
    })
    assert response.status_code == 200
    assert response.json()["provider"] == "ollama"


def test_paid_with_cloud_scope_keeps_explicit_approval_gate(signed_access, monkeypatch):
    async def synthetic_budget():
        return None
    async def synthetic_image(*_args, **_kwargs):
        return {"model": "synthetic/model", "image": "data:image/png;base64,iVBORw0KGgo=",
                "cost": None, "media_type": "image/png"}
    monkeypatch.setattr(providers, "verify_cloud_key_budget", synthetic_budget)
    monkeypatch.setattr(providers, "image_request", synthetic_image)
    headers = signed_access("paid", "cloud")
    denied = client.post("/api/v1/images", headers=headers, json={
        "prompt": "synthetic sunrise", "approve_paid_generation": False})
    assert denied.status_code == 403
    accepted = client.post("/api/v1/images", headers=headers, json={
        "prompt": "synthetic sunrise", "approve_paid_generation": True})
    assert accepted.status_code == 200
    assert accepted.json()["cost"] is None
