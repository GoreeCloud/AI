"""Synthetic signed JWTs, offline encrypted backups and owner-approved retention."""
import base64
import json
import os
import sqlite3
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.testclient import TestClient

os.environ["GOREECLOUD_AI_TOKEN"] = "test-owner-token"

from app import backup, storage  # noqa: E402
from app.main import app  # noqa: E402
from app.security import _oidc_claims  # noqa: E402

client = TestClient(app)
OWNER = {"Authorization": "Bearer test-owner-token"}


@pytest.fixture
def oidc_keys(tmp_path, monkeypatch):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key()))
    jwk.update({"kid": "test-only-kid", "alg": "RS256", "use": "sig"})
    path = tmp_path / "issuer-public-keys.json"
    path.write_text(json.dumps({"keys": [jwk]}))
    path.chmod(0o600)
    monkeypatch.setenv("GOREECLOUD_AI_AUTH_MODE", "oidc")
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_ISSUER", "https://identity.example.test/realms/goree")
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_AUDIENCE", "goreecloud-ai")
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_OWNER_SUB", "synthetic-owner")
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_REQUIRED_SCOPE", "goreecloud.ai.owner")
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_JWKS_PATH", str(path))
    def mint(**overrides):
        now = datetime.now(UTC)
        claims = {"iss": "https://identity.example.test/realms/goree", "aud": "goreecloud-ai",
                  "sub": "synthetic-owner", "iat": now, "nbf": now,
                  "exp": now + timedelta(minutes=5), "scope": "goreecloud.ai.owner"}
        claims.update(overrides)
        return jwt.encode(claims, private, algorithm="RS256", headers={"kid": "test-only-kid"})
    return mint, path


def test_owner_token_not_accepted_in_oidc_mode(oidc_keys):
    mint, _ = oidc_keys
    assert client.get("/api/v1/models", headers=OWNER).status_code == 401
    assert client.get("/api/v1/models",
                      headers={"Authorization": "Bearer " + mint()}).status_code == 200


@pytest.mark.parametrize("change", [
    {"iss": "https://evil.example.test"}, {"aud": "wrong-audience"},
    {"sub": "another-person"}, {"scope": "goreecloud.ai.viewer"},
    {"exp": datetime(2000, 1, 1, tzinfo=UTC)},
    {"nbf": datetime(3000, 1, 1, tzinfo=UTC)},
])
def test_oidc_rejects_bad_claims(oidc_keys, change):
    mint, _ = oidc_keys
    with pytest.raises(HTTPException) as error:
        _oidc_claims(mint(**change))
    assert error.value.status_code == 401


def test_oidc_jwks_path_permissions_and_issuer(oidc_keys, monkeypatch):
    mint, path = oidc_keys
    path.chmod(0o644)
    with pytest.raises(HTTPException) as error:
        _oidc_claims(mint())
    assert error.value.status_code == 401
    path.chmod(0o600)
    monkeypatch.setenv("GOREECLOUD_AI_OIDC_ISSUER", "http://insecure.example.test")
    with pytest.raises(HTTPException) as error:
        _oidc_claims(mint())
    assert error.value.status_code == 503


def test_encrypted_backup_restore_round_trip(tmp_path, monkeypatch):
    db = tmp_path / "data" / "ai.sqlite3"
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(db))
    secret = "private-hobby-note"
    row = storage.create_document("Confidential", secret)
    monkeypatch.setenv("GOREECLOUD_AI_BACKUP_KEY", base64.b64encode(os.urandom(32)).decode())
    archive = tmp_path / "backup" / "snapshot.gcai"
    backup.backup(db, archive)
    encrypted = archive.read_bytes()
    assert secret.encode() not in encrypted
    assert encrypted.startswith(backup.MAGIC)
    assert archive.stat().st_mode & 0o077 == 0
    target = tmp_path / "restored" / "ai.sqlite3"
    backup.restore(archive, target)
    with sqlite3.connect(target) as conn:
        assert conn.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        assert conn.execute("SELECT body FROM documents WHERE id=?", (row["id"],)).fetchone()[0] == secret
    assert target.stat().st_mode & 0o077 == 0
    with pytest.raises(FileExistsError):
        backup.restore(archive, target)
    with pytest.raises(FileExistsError):
        backup.backup(db, archive)


def test_backup_rejects_wrong_key_and_tampering(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite3"
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(db))
    storage.create_document("Test", "This should remain private")
    key = base64.b64encode(os.urandom(32)).decode()
    monkeypatch.setenv("GOREECLOUD_AI_BACKUP_KEY", key)
    archive = tmp_path / "snapshot.gcai"
    backup.backup(db, archive)
    target = tmp_path / "restore.sqlite3"
    monkeypatch.setenv("GOREECLOUD_AI_BACKUP_KEY", base64.b64encode(os.urandom(32)).decode())
    with pytest.raises(InvalidTag):
        backup.restore(archive, target)
    assert not target.exists()
    monkeypatch.setenv("GOREECLOUD_AI_BACKUP_KEY", key)
    raw = bytearray(archive.read_bytes())
    raw[-1] ^= 1
    archive.write_bytes(raw)
    with pytest.raises(InvalidTag):
        backup.restore(archive, target)
    assert not target.exists()


def test_retention_explicit_approval(tmp_path, monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(tmp_path / "db.sqlite3"))
    monkeypatch.setenv("GOREECLOUD_AI_CONVERSATION_RETENTION_DAYS", "30")
    old = storage.save_conversation("Old private chat", [{"role": "user", "content": "Sensitive"}])
    recent = storage.save_conversation("New private chat", [{"role": "user", "content": "Keep"}])
    with storage._connection() as db:
        db.execute("UPDATE conversations SET updated_at=? WHERE id=?",
                   ((datetime.now(UTC) - timedelta(days=60)).isoformat(), old["id"]))
    assert client.post("/api/v1/privacy/purge-expired", json={"approved": True}).status_code == 401
    assert client.post("/api/v1/privacy/purge-expired", headers=OWNER,
                       json={"approved": False}).status_code == 403
    assert storage.get_conversation(old["id"]) is not None
    response = client.post("/api/v1/privacy/purge-expired", headers=OWNER, json={"approved": True})
    assert response.status_code == 200
    assert response.json()["deleted_conversations"] == 1
    assert storage.get_conversation(old["id"]) is None
    assert storage.get_conversation(recent["id"]) is not None
    with storage._connection() as db:
        assert db.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 1



def test_ollama_endpoint_misleading_hosts_rejected(monkeypatch):
    from app import providers

    bad = [
        "http://127.0.0.1:11434@evil.example.test",
        "http://127.0.0.1:11434/proxy",
        "http://127.0.0.1:notaport",
        "http://127.0.0.1:11434?transfer=secret",
        "http://127.0.0.1:11434#fragment",
        "http://localho.st:11434",
        "http://192.168.1.5:11434",
        "https://evil.example.test:11434",
    ]
    for url in bad:
        monkeypatch.setenv("OLLAMA_BASE_URL", url)
        monkeypatch.delenv("GOREECLOUD_AI_ALLOW_REMOTE_OLLAMA", raising=False)
        with pytest.raises(HTTPException):
            providers.local_url()

    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    assert providers.local_url() == "http://127.0.0.1:11434"

    monkeypatch.setenv("GOREECLOUD_AI_ALLOW_REMOTE_OLLAMA", "true")
    monkeypatch.setenv("OLLAMA_BASE_URL", "https://ollama.example.test:11434")
    assert providers.local_url() == "https://ollama.example.test:11434"
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.example.test:11434")
    with pytest.raises(HTTPException):
        providers.local_url()
