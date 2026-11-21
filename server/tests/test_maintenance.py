"""Local retention maintenance is disabled by default; synthetic-only tests."""
import base64
import os
from datetime import UTC, datetime, timedelta

import pytest

from app import maintenance, storage


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    now = datetime(2026, 11, 21, 14, 0, tzinfo=UTC)
    db_path = tmp_path / "test-maintenance.sqlite3"
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(db_path))
    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "plaintext")
    monkeypatch.setenv("GOREECLOUD_AI_CONVERSATION_RETENTION_DAYS", "30")
    monkeypatch.setenv("GOREECLOUD_AI_CONSENT_RECEIPT_RETENTION_DAYS", "14")
    monkeypatch.delenv("GOREECLOUD_AI_MAINTENANCE_ENABLED", raising=False)
    old = storage.save_conversation("Old", [{"role": "user", "content": "old-only-private-text"}])
    recent = storage.save_conversation("Recent", [{"role": "user", "content": "recent-only-private-text"}])
    with storage._connection() as db:
        db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (
            (now - timedelta(days=48)).isoformat(), old["id"]))
        db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (
            (now - timedelta(days=1)).isoformat(), recent["id"]))
        for delta in (1, 20):
            db.execute(
                "INSERT INTO cloud_consent_receipts VALUES (?, ?, ?, ?)",
                (f"receipt-{delta}", (now - timedelta(days=delta)).isoformat(),
                 "chat", "cloud-processing-consent"),
            )
            db.execute(
                "INSERT INTO paid_call_admissions VALUES (?, ?, ?)",
                (f"admission-{delta}", (now - timedelta(days=delta)).date().isoformat(), "chat"),
            )
    return now, db_path, old["id"], recent["id"]


def test_dry_run_no_changes_including_sensitive_data(synthetic, capsys):
    now, path, old_id, recent_id = synthetic
    original = path.read_bytes()
    result = maintenance.run(now=now)
    assert result["applied"] is False
    assert (result["eligible_conversations"], result["eligible_receipts"],
            result["eligible_old_admissions"]) == (1, 1, 1)
    assert path.read_bytes() == original
    assert storage.get_conversation(old_id) is not None
    assert storage.get_conversation(recent_id) is not None
    assert "old-only-private-text" not in str(result)
    assert "recent-only-private-text" not in str(result)
    assert not capsys.readouterr().err


def test_apply_denied_without_explicit_enablement(synthetic):
    now, path, old_id, _recent = synthetic
    original = path.read_bytes()
    with pytest.raises(PermissionError):
        maintenance.run(apply=True, now=now)
    assert path.read_bytes() == original
    assert storage.get_conversation(old_id) is not None


def test_apply_removes_only_expired_rows_and_is_idempotent(synthetic, monkeypatch):
    now, _path, old_id, recent_id = synthetic
    monkeypatch.setenv("GOREECLOUD_AI_MAINTENANCE_ENABLED", "true")
    summary = maintenance.run(apply=True, now=now)
    assert summary["applied"] is True
    assert (summary["eligible_conversations"], summary["eligible_receipts"],
            summary["eligible_old_admissions"]) == (1, 1, 1)
    assert storage.get_conversation(old_id) is None
    assert storage.get_conversation(recent_id)["messages"][0]["content"] == "recent-only-private-text"
    with storage._connection() as db:
        assert db.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 1
        assert db.execute("SELECT id FROM cloud_consent_receipts").fetchall()[0][0] == "receipt-1"
        assert db.execute("SELECT id FROM paid_call_admissions").fetchall()[0][0] == "admission-1"
    again = maintenance.run(apply=True, now=now)
    assert (again["eligible_conversations"], again["eligible_receipts"],
            again["eligible_old_admissions"]) == (0, 0, 0)


def test_disabled_conversation_expiration_never_removes_chats(synthetic, monkeypatch):
    now, _path, old_id, _recent = synthetic
    monkeypatch.setenv("GOREECLOUD_AI_MAINTENANCE_ENABLED", "true")
    monkeypatch.setenv("GOREECLOUD_AI_CONVERSATION_RETENTION_DAYS", "0")
    summary = maintenance.run(apply=True, now=now)
    assert summary["eligible_conversations"] == 0
    assert storage.get_conversation(old_id) is not None
    assert summary["eligible_receipts"] == 1


@pytest.mark.parametrize("key,value", [
    ("GOREECLOUD_AI_MAINTENANCE_ENABLED", "enabled"),
    ("GOREECLOUD_AI_CONVERSATION_RETENTION_DAYS", "-1"),
    ("GOREECLOUD_AI_CONSENT_RECEIPT_RETENTION_DAYS", "9999"),
])
def test_invalid_policy_denied_before_changes(synthetic, monkeypatch, key, value):
    now, path, _old, _recent = synthetic
    before = path.read_bytes()
    monkeypatch.setenv(key, value)
    with pytest.raises((ValueError, Exception)) as error:
        maintenance.run(apply=True, now=now)
    assert error.value
    assert path.read_bytes() == before


def test_does_not_create_database_when_missing(tmp_path, monkeypatch):
    path = tmp_path / "new.sqlite3"
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(path))
    monkeypatch.setenv("GOREECLOUD_AI_MAINTENANCE_ENABLED", "true")
    with pytest.raises(FileNotFoundError):
        maintenance.run(apply=True)
    assert not path.exists()


def test_requires_aware_utc_time(synthetic, monkeypatch):
    _now, _path, *_ = synthetic
    monkeypatch.setenv("GOREECLOUD_AI_MAINTENANCE_ENABLED", "true")
    with pytest.raises(ValueError):
        maintenance.run(apply=True, now=datetime(2026, 11, 21))


def test_command_prints_counts_not_content(synthetic, monkeypatch, capsys):
    now, _path, *_ = synthetic
    monkeypatch.setattr(maintenance, "run", lambda **kw: {
        "applied": kw.get("apply", False),
        "eligible_conversations": 1, "eligible_receipts": 2,
        "eligible_old_admissions": 3,
    })
    monkeypatch.setattr("sys.argv", ["maintenance"])
    maintenance.main()
    output = capsys.readouterr().out
    assert "Dry run" in output and "conversations=1" in output
    assert "private-text" not in output
    monkeypatch.setattr("sys.argv", ["maintenance", "--apply"])
    maintenance.main()
    assert "Applied" in capsys.readouterr().out


def test_sqlcipher_retention_stays_encrypted(tmp_path, monkeypatch):
    pytest.importorskip("sqlcipher3")
    path = tmp_path / "cipher.sqlite3"
    monkeypatch.setenv("GOREECLOUD_AI_DB_PATH", str(path))
    monkeypatch.setenv("GOREECLOUD_AI_DB_MODE", "sqlcipher")
    monkeypatch.setenv("GOREECLOUD_AI_DB_KEY", base64.b64encode(os.urandom(32)).decode())
    monkeypatch.setenv("GOREECLOUD_AI_MAINTENANCE_ENABLED", "true")
    monkeypatch.setenv("GOREECLOUD_AI_CONVERSATION_RETENTION_DAYS", "1")
    monkeypatch.setenv("GOREECLOUD_AI_CONSENT_RECEIPT_RETENTION_DAYS", "2")
    old = storage.save_conversation("Secret", [{"role": "user", "content": "only ciphertext"}])
    with storage._connection() as db:
        db.execute("UPDATE conversations SET updated_at=? WHERE id=?",
                   ((datetime.now(UTC) - timedelta(days=7)).isoformat(), old["id"]))
    original_bytes = path.read_bytes()
    preview = maintenance.run()
    assert preview["eligible_conversations"] == 1
    assert path.read_bytes() == original_bytes
    summary = maintenance.run(apply=True)
    assert summary["eligible_conversations"] == 1
    assert storage.get_conversation(old["id"]) is None
    assert not path.read_bytes().startswith(b"SQLite format 3\x00")
    assert b"only ciphertext" not in path.read_bytes()
