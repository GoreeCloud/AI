"""Operator-controlled, content-free local retention housekeeping.

Safe for an explicitly configured systemd timer only after deployment review.
Preview is read-only. Apply requires a separate enabled flag AND --apply.
No cloud/provider access, prompt telemetry or automatic startup work.
"""
import argparse
import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path

from . import database, storage


def _enabled() -> bool:
    value = os.getenv("GOREECLOUD_AI_MAINTENANCE_ENABLED", "false").lower()
    if value not in ("true", "false"):
        raise ValueError("Invalid maintenance enablement policy")
    return value == "true"


def _preview_connection(path: Path):
    """True read-only SQLite/SQLCipher connection, no schema creation or migration."""
    mode = database.database_mode()
    database._check_path(path, mode, create=False)
    driver = database._sqlcipher_driver() if mode == "sqlcipher" else sqlite3
    key = database._database_key() if mode == "sqlcipher" else None
    db = driver.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
    try:
        if key is not None:
            db.execute("PRAGMA key = " + '"' + "x'" + key.hex() + "'" + '"')
        db.execute("SELECT count(*) FROM sqlite_master").fetchone()
        return db
    except Exception:
        db.close()
        raise ValueError("Maintenance preview cannot open configured database") from None


def run(*, apply: bool = False, now: datetime | None = None) -> dict:
    if apply and not _enabled():
        raise PermissionError("Retention maintenance must be explicitly enabled")
    if not apply:
        _enabled()  # A misspelled configuration is not silently accepted.
    days = storage.conversation_retention_days()
    receipt_days = storage._consent_retention_days()
    instant = now or datetime.now(UTC)
    if instant.tzinfo is None:
        raise ValueError("Retention time must be timezone aware")
    instant = instant.astimezone(UTC)
    conv_cutoff = (instant - timedelta(days=days)).isoformat() if days else None
    receipt_cutoff = (instant - timedelta(days=receipt_days)).isoformat()
    admission_cutoff = (instant - timedelta(days=14)).date().isoformat()
    path = Path(os.getenv("GOREECLOUD_AI_DB_PATH", "./data/ai.sqlite3")).expanduser()
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError("Maintenance requires an existing private database")

    connection = storage._connection() if apply else closing(_preview_connection(path))
    with connection as db:
        if apply:
            db.execute("BEGIN IMMEDIATE")
        conv_count = (
            db.execute("SELECT COUNT(*) FROM conversations WHERE updated_at < ?",
                       (conv_cutoff,)).fetchone()[0] if conv_cutoff else 0
        )
        receipts = db.execute(
            "SELECT COUNT(*) FROM cloud_consent_receipts WHERE created_at < ?",
            (receipt_cutoff,)).fetchone()[0]
        admissions = db.execute(
            "SELECT COUNT(*) FROM paid_call_admissions WHERE day < ?",
            (admission_cutoff,)).fetchone()[0]
        if apply:
            if conv_cutoff:
                db.execute("DELETE FROM conversations WHERE updated_at < ?", (conv_cutoff,))
            db.execute("DELETE FROM cloud_consent_receipts WHERE created_at < ?",
                       (receipt_cutoff,))
            db.execute("DELETE FROM paid_call_admissions WHERE day < ?",
                       (admission_cutoff,))
    return {
        "applied": apply,
        "conversation_policy_days": days,
        "consent_receipt_policy_days": receipt_days,
        "eligible_conversations": conv_count,
        "eligible_receipts": receipts,
        "eligible_old_admissions": admissions,
        "note": (
            "Live local rows only, not secure erasure. Backups, replicas, "
            "freelist pages and external provider content are unaffected."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview or explicitly apply GoreeCloud AI local retention policy"
    )
    parser.add_argument("--apply", action="store_true",
                        help="Delete expired rows only if GOREECLOUD_AI_MAINTENANCE_ENABLED=true")
    args = parser.parse_args()
    try:
        result = run(apply=args.apply)
    except Exception as exc:
        # No database path, content, credentials, or private stack trace in stdout/stderr.
        raise SystemExit("Local retention maintenance failed: " + type(exc).__name__) from None
    stage = "Applied" if result["applied"] else "Preview"
    print(stage + " retention counts only: conversations=" + str(result["eligible_conversations"])
          + ", receipts=" + str(result["eligible_receipts"])
          + ", old_admissions=" + str(result["eligible_old_admissions"]))
    if not result["applied"]:
        print("Dry run: no data deleted; --apply additionally needs explicit enablement.")


if __name__ == "__main__":
    main()
