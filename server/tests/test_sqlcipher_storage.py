"""Real SQLCipher FTS/live data/recovery tests using only disposable synthetic files."""
import base64
import os
import sqlite3
from pathlib import Path

import pytest
from fastapi import HTTPException

from app import backup, database, migrate_sqlcipher, storage

pytest.importorskip("sqlcipher3")


@pytest.fixture
def secrets(tmp_path, monkeypatch):
    key = base64.b64encode(os.urandom(32)).decode("ascii")
    backup_key = base64.b64encode(os.urandom(32)).decode("ascii")
    monkeypatch.setenv("GOREECLOUD_AI_DB_KEY", key)
    monkeypatch.setenv("GOREECLOUD_AI_BACKUP_KEY", backup_key)
    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "plaintext")
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(tmp_path / "original.sqlite3"))
    return tmp_path, key


def test_migrate_plaintext_preserves_fts_and_original(secrets, monkeypatch):
    tmp_path, key = secrets
    original = Path(os.environ["GOREECLOUD_AI_DB_PATH"])
    doc = storage.create_document("Visible fixture", "Synthetic privately indexed meteorite")
    snap = storage.save_conversation("Test", [{"role": "user", "content": "Synthetic conversation"}])
    assert storage.search_documents("meteorite")
    dest = tmp_path / "encrypted" / "ai.sqlite3"
    original_snapshot = original.read_bytes()
    migrate_sqlcipher.migrate(original, dest)
    assert original.read_bytes() == original_snapshot
    assert original.read_bytes().startswith(database.SQLITE_HEADER)
    cipher_data = dest.read_bytes()
    assert not cipher_data.startswith(database.SQLITE_HEADER)
    assert b"Synthetic privately indexed meteorite" not in cipher_data
    assert b"Synthetic conversation" not in cipher_data
    assert dest.stat().st_mode & 0o077 == 0

    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "sqlcipher")
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(dest))
    assert storage.get_document(doc["id"])["body"] == "Synthetic privately indexed meteorite"
    assert storage.search_documents("meteorite")[0]["id"] == doc["id"]
    assert storage.get_conversation(snap["id"])["messages"][0]["content"] == "Synthetic conversation"
    assert storage.create_document("Encrypted now", "More protected private text")
    assert b"More protected private text" not in dest.read_bytes()
    with pytest.raises(FileExistsError):
        migrate_sqlcipher.migrate(original, dest)

    monkeypatch.setenv("GOREECLOUD_AI_DB_KEY", base64.b64encode(os.urandom(32)).decode())
    with pytest.raises(HTTPException) as exc:
        storage.get_document(doc["id"])
    assert exc.value.status_code == 503
    monkeypatch.setenv("GOREECLOUD_AI_DB_KEY", key)
    assert storage.get_document(doc["id"])["id"] == doc["id"]


def test_new_encrypted_database_fts_key_and_format_fails_closed(secrets, monkeypatch):
    tmp_path, key = secrets
    new_path = tmp_path / "encrypted-fresh.sqlite3"
    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "sqlcipher")
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(new_path))
    created = storage.create_document("New", "Encrypted indexing retained")
    assert storage.search_documents("indexing")[0]["id"] == created["id"]
    assert not new_path.read_bytes().startswith(database.SQLITE_HEADER)
    monkeypatch.delenv("GOREECLOUD_AI_DB_KEY")
    with pytest.raises(HTTPException) as exc:
        storage.list_documents()
    assert exc.value.status_code == 503
    monkeypatch.setenv("GOREECLOUD_AI_DB_KEY", key)
    assert storage.get_document(created["id"]) is not None
    # Do not permit accidental opens of a ciphertext database using sqlite3.
    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "plaintext")
    with pytest.raises(HTTPException):
        storage.list_documents()
    assert not new_path.read_bytes().startswith(database.SQLITE_HEADER)


def test_no_implicit_plaintext_to_encrypted_transition(secrets, monkeypatch):
    tmp_path, _ = secrets
    original = Path(os.environ["GOREECLOUD_AI_DB_PATH"])
    storage.create_document("Original", "Retain source")
    before = original.read_bytes()
    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "sqlcipher")
    with pytest.raises(HTTPException) as exc:
        storage.list_documents()
    assert exc.value.status_code == 503
    assert original.read_bytes() == before
    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "not-a-mode")
    with pytest.raises(HTTPException):
        storage.list_documents()


def test_encrypted_backup_restores_encrypted_and_rejects_mismatched_mode(secrets, monkeypatch):
    tmp_path, key = secrets
    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "sqlcipher")
    db_path = tmp_path / "enc.sqlite3"
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(db_path))
    doc = storage.create_document("Private", "Encryption plus backup synthetic secret")
    archive = tmp_path / "backup" / "enc.gcai"
    backup.backup(db_path, archive)
    assert archive.read_bytes().startswith(backup.MAGIC_SQLCIPHER)
    assert b"Encryption plus backup synthetic secret" not in archive.read_bytes()
    restored = tmp_path / "restore" / "enc.sqlite3"
    backup.restore(archive, restored)
    assert not restored.read_bytes().startswith(database.SQLITE_HEADER)
    assert b"Encryption plus backup synthetic secret" not in restored.read_bytes()
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(restored))
    assert storage.get_document(doc["id"])["body"] == "Encryption plus backup synthetic secret"
    monkeypatch.setenv("GOREECLOUD_AI_DB_KEY", base64.b64encode(os.urandom(32)).decode())
    with pytest.raises(HTTPException):
        backup.restore(archive, tmp_path / "bad" / "wrong.sqlite3")
    monkeypatch.setenv("GOREECLOUD_AI_DB_KEY", key)
    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "plaintext")
    with pytest.raises(ValueError):
        backup.restore(archive, tmp_path / "bad" / "plain.sqlite3")


def test_migration_rejects_untrusted_source_and_retains_destination(secrets, tmp_path, monkeypatch):
    original = Path(os.environ["GOREECLOUD_AI_DB_PATH"])
    storage.create_document("Source", "Value")
    target = tmp_path / "target.sqlite3"
    target.write_bytes(b"preserve-existing")
    with pytest.raises(FileExistsError):
        migrate_sqlcipher.migrate(original, target)
    assert target.read_bytes() == b"preserve-existing"
    unsupported = tmp_path / "unsupported.sqlite3"
    unsupported.write_bytes(b"not-sqlite")
    unsupported.chmod(0o600)
    with pytest.raises(ValueError):
        migrate_sqlcipher.migrate(unsupported, tmp_path / "new.sqlite3")
    assert not (tmp_path / "new.sqlite3").exists()


def test_plaintext_legacy_driver_handles_group_readable_existing_file(secrets):
    source = Path(os.environ["GOREECLOUD_AI_DB_PATH"])
    with sqlite3.connect(source) as raw:
        raw.execute("CREATE TABLE documents(id text, title text, body text, updated_at text)")
    source.chmod(0o644)
    assert storage.list_documents() == []
    assert source.stat().st_mode & 0o077 == 0
