"""Local SQLite documents; stored unencrypted in operator-controlled data directory."""
import os
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path


def _connection():
    path = Path(os.getenv("GOREECLOUD_AI_DB_PATH", "./data/ai.sqlite3")).expanduser()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS documents
        (id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL, updated_at TEXT NOT NULL)""")
    return conn

def list_documents() -> list[dict]:
    with _connection() as db:
        return [dict(x) for x in db.execute(
            "SELECT id,title,updated_at FROM documents ORDER BY updated_at DESC LIMIT 200"
        ).fetchall()]

def create_document(title: str, body: str) -> dict:
    item = {"id": str(uuid.uuid4()), "title": title, "body": body,
            "updated_at": datetime.now(UTC).isoformat()}
    with _connection() as db:
        db.execute("INSERT INTO documents VALUES (:id,:title,:body,:updated_at)", item)
        db.commit()
    return item

def get_document(doc_id: str) -> dict | None:
    with _connection() as db:
        row = db.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
    return dict(row) if row else None

def update_document(doc_id: str, title: str, body: str) -> dict | None:
    with _connection() as db:
        db.execute("UPDATE documents SET title=?,body=?,updated_at=? WHERE id=?",
                   (title, body, datetime.now(UTC).isoformat(), doc_id))
        db.commit()
    return get_document(doc_id)
