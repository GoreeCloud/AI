"""Real synthetic SQLCipher key rotation tests: source preserved, safe failures."""
import base64
import os

import pytest
from fastapi import HTTPException

from app import database, rotate_sqlcipher, storage

pytest.importorskip("sqlcipher3")


def _new_key() -> str:
    return base64.b64encode(os.urandom(32)).decode("ascii")


@pytest.fixture
def sample(tmp_path, monkeypatch):
    original_key, replacement = _new_key(), _new_key()
    original = tmp_path / "encrypted.sqlite3"
    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "sqlcipher")
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(original))
    monkeypatch.setenv("GOREECLOUD_AI_DB_KEY", original_key)
    monkeypatch.setenv("GOREECLOUD_AI_NEW_DB_KEY", replacement)
    record = storage.create_document("Private synthetic", "A cerulean comet crossed the moon")
    conversation = storage.save_conversation("Synthetic conversation", [
        {"role": "user", "content": "Private sample record"}
    ])
    assert storage.search_documents("cerulean")[0]["id"] == record["id"]
    return original, original_key, replacement, record, conversation


def test_successful_rotation_preserves_old_bytes_and_fts(sample, tmp_path, monkeypatch):
    original, old_key, new_key, record, conv = sample
    before = original.read_bytes()
    output = tmp_path / "new-key" / "encrypted.sqlite3"
    rotate_sqlcipher.rotate(original, output)
    assert original.read_bytes() == before
    assert output.stat().st_mode & 0o077 == 0
    assert not output.read_bytes().startswith(database.SQLITE_HEADER)
    assert b"cerulean comet" not in output.read_bytes()

    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(output))
    with pytest.raises(HTTPException) as denied:
        storage.get_document(record["id"])
    assert denied.value.status_code == 503
    monkeypatch.setenv("GOREECLOUD_AI_DB_KEY", new_key)
    assert storage.get_document(record["id"])["body"].endswith("the moon")
    assert storage.search_documents("cerulean")[0]["id"] == record["id"]
    assert storage.get_conversation(conv["id"])["messages"][0]["content"] == "Private sample record"

    monkeypatch.setenv("GOREECLOUD_AI_DB_KEY", old_key)
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(original))
    assert storage.get_document(record["id"])["id"] == record["id"]
    with pytest.raises(FileExistsError):
        rotate_sqlcipher.rotate(original, output)


def test_missing_or_equal_next_key_does_not_write(sample, tmp_path, monkeypatch):
    original, old_key, _new, *_ = sample
    out = tmp_path / "should-not-be-created.sqlite3"
    before = original.read_bytes()
    monkeypatch.delenv("GOREECLOUD_AI_NEW_DB_KEY")
    with pytest.raises(ValueError):
        rotate_sqlcipher.rotate(original, out)
    monkeypatch.setenv("GOREECLOUD_AI_NEW_DB_KEY", old_key)
    with pytest.raises(ValueError):
        rotate_sqlcipher.rotate(original, out)
    monkeypatch.setenv("GOREECLOUD_AI_NEW_DB_KEY", "not-base64")
    with pytest.raises(ValueError):
        rotate_sqlcipher.rotate(original, out)
    assert original.read_bytes() == before
    assert not out.exists()


def test_plaintext_mode_and_wrong_current_key_denied(sample, tmp_path, monkeypatch):
    original, _old, _new, *_ = sample
    out = tmp_path / "no-output.sqlite3"
    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "plaintext")
    with pytest.raises(ValueError):
        rotate_sqlcipher.rotate(original, out)
    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "sqlcipher")
    monkeypatch.setenv("GOREECLOUD_AI_DB_KEY", _new_key())
    with pytest.raises(HTTPException):
        rotate_sqlcipher.rotate(original, out)
    assert not out.exists()


def test_existing_destination_or_wal_sidecar_is_not_modified(sample, tmp_path):
    original, *_ = sample
    out = tmp_path / "occupied.sqlite3"
    out.write_bytes(b"existing-private-output")
    with pytest.raises(FileExistsError):
        rotate_sqlcipher.rotate(original, out)
    assert out.read_bytes() == b"existing-private-output"
    wal = original.parent / (original.name + "-wal")
    wal.write_bytes(b"synthetic-no-delete-wal")
    fresh = tmp_path / "unused.sqlite3"
    with pytest.raises(ValueError):
        rotate_sqlcipher.rotate(original, fresh)
    assert wal.read_bytes() == b"synthetic-no-delete-wal"
    assert not fresh.exists()


def test_rotation_requires_private_destination_folder(sample, tmp_path):
    original, *_ = sample
    unsafe = tmp_path / "public-folder"
    unsafe.mkdir(mode=0o777)
    unsafe.chmod(0o777)
    with pytest.raises(ValueError):
        rotate_sqlcipher.rotate(original, unsafe / "new.sqlite3")
    assert not (unsafe / "new.sqlite3").exists()


def test_rotation_cli_sanitizes_errors(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(rotate_sqlcipher, "rotate", lambda *_: (_ for _ in ()).throw(
        ValueError("sensitive-fixture-path-only")))
    monkeypatch.setattr("sys.argv", ["rotate_sqlcipher", "--source", str(tmp_path / "private"),
                                   "--output", str(tmp_path / "target")])
    with pytest.raises(SystemExit) as error:
        rotate_sqlcipher.main()
    assert "sensitive-fixture" not in str(error.value)
    assert "ValueError" in str(error.value)
    assert not capsys.readouterr().out
