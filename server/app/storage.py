"""Local single-owner storage.

Documents and saved conversations are deliberately opt-in and NOT encrypted at
rest. FTS5 indexes live in the same private SQLite file. No prompt/secret logs.
"""
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException


def _now() -> str:
    return datetime.now(UTC).isoformat()


@contextmanager
def _connection():
    path = Path(os.getenv("GOREECLOUD_AI_DB_PATH", "./data/ai.sqlite3")).expanduser()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        raise RuntimeError("Database path must not be a symlink")
    db = sqlite3.connect(path, timeout=10)
    try:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=10000")
        db.execute("""CREATE TABLE IF NOT EXISTS documents
            (id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL, updated_at TEXT NOT NULL)""")
        db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS document_fts USING
            fts5(title, body, content='documents', content_rowid='rowid')""")
        db.executescript("""
            CREATE TRIGGER IF NOT EXISTS document_insert AFTER INSERT ON documents BEGIN
                INSERT INTO document_fts(rowid, title, body) VALUES (new.rowid, new.title, new.body);
            END;
            CREATE TRIGGER IF NOT EXISTS document_delete AFTER DELETE ON documents BEGIN
                INSERT INTO document_fts(document_fts, rowid, title, body)
                VALUES ('delete', old.rowid, old.title, old.body);
            END;
            CREATE TRIGGER IF NOT EXISTS document_update AFTER UPDATE ON documents BEGIN
                INSERT INTO document_fts(document_fts, rowid, title, body)
                VALUES ('delete', old.rowid, old.title, old.body);
                INSERT INTO document_fts(rowid, title, body) VALUES (new.rowid, new.title, new.body);
            END;
        """)
        if db.execute("PRAGMA user_version").fetchone()[0] < 1:
            db.execute("INSERT INTO document_fts(document_fts) VALUES ('rebuild')")
            db.execute("PRAGMA user_version=1")
        db.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','assistant')),
            content TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE)""")
        db.execute("CREATE INDEX IF NOT EXISTS messages_conversation ON messages(conversation_id, created_at)")
        db.execute("""CREATE TABLE IF NOT EXISTS paid_call_admissions (
            id TEXT PRIMARY KEY, day TEXT NOT NULL, kind TEXT NOT NULL)""")
        db.execute("CREATE INDEX IF NOT EXISTS paid_call_day ON paid_call_admissions(day)")
        db.commit()
        if not path.exists():
            raise RuntimeError("Database could not be initialized")
        path.chmod(0o600)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def list_documents() -> list[dict]:
    with _connection() as db:
        return [dict(row) for row in db.execute(
            "SELECT id,title,updated_at FROM documents ORDER BY updated_at DESC LIMIT 200")]


def create_document(title: str, body: str) -> dict:
    row = {"id": str(uuid.uuid4()), "title": title, "body": body, "updated_at": _now()}
    with _connection() as db:
        db.execute("INSERT INTO documents VALUES (:id,:title,:body,:updated_at)", row)
    return row


def get_document(doc_id: str) -> dict | None:
    with _connection() as db:
        row = db.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        return dict(row) if row else None


def update_document(doc_id: str, title: str, body: str) -> dict | None:
    with _connection() as db:
        cursor = db.execute(
            "UPDATE documents SET title=?, body=?, updated_at=? WHERE id=?",
            (title, body, _now(), doc_id))
        if cursor.rowcount != 1:
            return None
    return get_document(doc_id)


def delete_document(doc_id: str) -> bool:
    with _connection() as db:
        return db.execute("DELETE FROM documents WHERE id=?", (doc_id,)).rowcount == 1


def search_documents(query: str, limit: int = 8) -> list[dict]:
    """Bounded lexical retrieval; no embeddings or off-device transfer."""
    stop_words = {"where", "what", "when", "why", "how", "the", "is", "are", "does", "was", "with", "and", "for", "from", "this", "that", "have"}
    terms = [term for term in re.findall(r"[^\W_]{2,}", query, re.UNICODE)
             if term.casefold() not in stop_words][:8]
    if not terms:
        return []
    # Quote tokens, never expose SQLite MATCH operators through input. OR avoids
    # requiring every natural-language question word to occur in a document.
    expression = " OR ".join('"' + term + '"*' for term in terms)
    with _connection() as db:
        return [dict(row) for row in db.execute("""
            SELECT documents.id, documents.title,
                   snippet(document_fts, 1, '', '', '…', 32) AS excerpt,
                   bm25(document_fts) AS rank
              FROM document_fts JOIN documents ON documents.rowid=document_fts.rowid
             WHERE document_fts MATCH ?
             ORDER BY rank LIMIT ?
        """, (expression, max(1, min(limit, 20))))]


def save_conversation(title: str, messages: list[dict]) -> dict:
    if not messages:
        raise HTTPException(422, "Cannot save an empty conversation")
    now = _now()
    conversation_id = str(uuid.uuid4())
    with _connection() as db:
        db.execute("INSERT INTO conversations VALUES (?, ?, ?, ?)", (conversation_id, title, now, now))
        for message in messages:
            db.execute("INSERT INTO messages VALUES (?, ?, ?, ?, ?)", (
                str(uuid.uuid4()), conversation_id, message["role"], message["content"], now))
    return get_conversation(conversation_id) or {}


def list_conversations() -> list[dict]:
    with _connection() as db:
        return [dict(row) for row in db.execute("""
            SELECT conversations.id, conversations.title, conversations.created_at,
                   conversations.updated_at, COUNT(messages.id) AS message_count
              FROM conversations LEFT JOIN messages ON messages.conversation_id=conversations.id
             GROUP BY conversations.id ORDER BY conversations.updated_at DESC LIMIT 200
        """)]


def get_conversation(conversation_id: str) -> dict | None:
    with _connection() as db:
        row = db.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone()
        if row is None:
            return None
        messages = db.execute("""
            SELECT role,content FROM messages WHERE conversation_id=?
            ORDER BY created_at, rowid""", (conversation_id,)).fetchall()
        return {**dict(row), "messages": [dict(message) for message in messages]}


def delete_conversation(conversation_id: str) -> bool:
    with _connection() as db:
        return db.execute("DELETE FROM conversations WHERE id=?", (conversation_id,)).rowcount == 1


def _daily_limit() -> int:
    try:
        amount = int(os.getenv("GOREECLOUD_AI_DAILY_CLOUD_REQUEST_LIMIT", "20"))
        if amount < 1 or amount > 10000:
            raise ValueError
        return amount
    except ValueError as exc:
        raise HTTPException(503, "Invalid operator cloud request-limit configuration") from exc


def cloud_quota() -> dict:
    day = datetime.now(UTC).date().isoformat()
    with _connection() as db:
        used = db.execute("SELECT COUNT(*) FROM paid_call_admissions WHERE day=?", (day,)).fetchone()[0]
    return {"day_utc": day, "limit": _daily_limit(), "admitted": used,
            "remaining": max(0, _daily_limit() - used),
            "note": "Request count guard, not a currency spending limit."}


def admit_cloud_call(kind: str) -> None:
    """Atomic daily request-count budget; rejected/failed calls still consume a slot."""
    limit = _daily_limit()
    day = datetime.now(UTC).date().isoformat()
    cutoff = (datetime.now(UTC) - timedelta(days=14)).date().isoformat()
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        admitted = db.execute(
            "SELECT COUNT(*) FROM paid_call_admissions WHERE day=?", (day,)).fetchone()[0]
        if admitted >= limit:
            raise HTTPException(429, "Daily external-provider request limit reached")
        db.execute("INSERT INTO paid_call_admissions VALUES (?, ?, ?)", (str(uuid.uuid4()), day, kind))
        db.execute("DELETE FROM paid_call_admissions WHERE day < ?", (cutoff,))
