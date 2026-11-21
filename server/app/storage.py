"""Local single-owner storage.

Documents and saved conversations are opt-in; the database supports optional
SQLCipher encryption of live storage and FTS5 indexes. Plain SQLite remains
default for compatibility. No prompt/secret logs.
"""
import os
import re
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException

from . import database


def _now() -> str:
    return datetime.now(UTC).isoformat()


@contextmanager
def _connection():
    path = Path(os.getenv("GOREECLOUD_AI_DB_PATH", "./data/ai.sqlite3")).expanduser()
    db = database.connect(path)
    try:
        db.row_factory = database.row_factory()
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
        db.execute("""CREATE TABLE IF NOT EXISTS document_revisions (
            id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
            title TEXT NOT NULL, body TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(document_id) REFERENCES documents(id) ON DELETE CASCADE)""")
        db.execute("""CREATE INDEX IF NOT EXISTS document_revision_order
            ON document_revisions(document_id, created_at DESC)""")
        db.execute("""CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('user','assistant')),
            content TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE)""")
        db.execute("CREATE INDEX IF NOT EXISTS messages_conversation ON messages(conversation_id, created_at)")
        # Upgrade existing local stores without rewriting their saved messages.
        # The external-content FTS5 index is rebuilt exactly once on creation.
        has_fts = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='message_fts'"
        ).fetchone() is not None
        db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS message_fts USING
            fts5(content, content='messages', content_rowid='rowid')""")
        db.executescript("""
            CREATE TRIGGER IF NOT EXISTS message_insert AFTER INSERT ON messages BEGIN
                INSERT INTO message_fts(rowid, content) VALUES (new.rowid, new.content);
            END;
            CREATE TRIGGER IF NOT EXISTS message_delete AFTER DELETE ON messages BEGIN
                INSERT INTO message_fts(message_fts, rowid, content)
                VALUES ('delete', old.rowid, old.content);
            END;
            CREATE TRIGGER IF NOT EXISTS message_update AFTER UPDATE ON messages BEGIN
                INSERT INTO message_fts(message_fts, rowid, content)
                VALUES ('delete', old.rowid, old.content);
                INSERT INTO message_fts(rowid, content) VALUES (new.rowid, new.content);
            END;
        """)
        if not has_fts:
            db.execute("INSERT INTO message_fts(message_fts) VALUES ('rebuild')")
        db.execute("""CREATE TABLE IF NOT EXISTS paid_call_admissions (
            id TEXT PRIMARY KEY, day TEXT NOT NULL, kind TEXT NOT NULL)""")
        db.execute("CREATE INDEX IF NOT EXISTS paid_call_day ON paid_call_admissions(day)")
        db.execute("""CREATE TABLE IF NOT EXISTS cloud_consent_receipts (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, kind TEXT NOT NULL,
            approval TEXT NOT NULL)""")
        db.execute("CREATE INDEX IF NOT EXISTS consent_receipt_created ON cloud_consent_receipts(created_at)")
        db.commit()
        if not path.exists():
            raise RuntimeError("Database could not be initialized")
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


def _snapshot_document(db, current: dict) -> str:
    """Private, bounded opt-in history. Store exactly the previous version."""
    revision_id = str(uuid.uuid4())
    db.execute(
        "INSERT INTO document_revisions VALUES (?, ?, ?, ?, ?)",
        (revision_id, current["id"], current["title"], current["body"], _now()),
    )
    db.execute("""
        DELETE FROM document_revisions
         WHERE document_id=? AND id NOT IN (
            SELECT id FROM document_revisions WHERE document_id=?
            ORDER BY created_at DESC, rowid DESC LIMIT 20
         )
    """, (current["id"], current["id"]))
    return revision_id


def update_document(doc_id: str, title: str, body: str,
                    record_revision: bool = False) -> dict | None:
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        if previous is None:
            return None
        if previous["title"] != title or previous["body"] != body:
            if record_revision:
                _snapshot_document(db, dict(previous))
            db.execute("UPDATE documents SET title=?, body=?, updated_at=? WHERE id=?",
                       (title, body, _now(), doc_id))
    return get_document(doc_id)


def list_document_revisions(doc_id: str) -> list[dict] | None:
    with _connection() as db:
        if db.execute("SELECT 1 FROM documents WHERE id=?", (doc_id,)).fetchone() is None:
            return None
        return [dict(row) for row in db.execute("""
            SELECT id, document_id, title, created_at,
                   length(body) AS body_characters
              FROM document_revisions WHERE document_id=?
             ORDER BY created_at DESC, rowid DESC LIMIT 20
        """, (doc_id,))]


def get_document_revision(doc_id: str, revision_id: str) -> dict | None:
    with _connection() as db:
        row = db.execute("""
            SELECT id, document_id, title, body, created_at
              FROM document_revisions WHERE document_id=? AND id=?
        """, (doc_id, revision_id)).fetchone()
        return dict(row) if row else None


def restore_document_revision(doc_id: str, revision_id: str) -> dict | None:
    """Atomic explicit restore with an undo snapshot of the displaced content."""
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        current = db.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        target = db.execute(
            "SELECT title, body FROM document_revisions WHERE document_id=? AND id=?",
            (doc_id, revision_id),
        ).fetchone()
        if current is None or target is None:
            return None
        if current["title"] != target["title"] or current["body"] != target["body"]:
            _snapshot_document(db, dict(current))
            db.execute(
                "UPDATE documents SET title=?, body=?, updated_at=? WHERE id=?",
                (target["title"], target["body"], _now(), doc_id),
            )
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



def rename_conversation(conversation_id: str, title: str) -> dict | None:
    """Rename an explicitly saved snapshot, without changing its message history."""
    new_title = title.strip()
    if not new_title or len(new_title) > 150:
        raise HTTPException(422, "Conversation title must be 1-150 non-space characters")
    with _connection() as db:
        changed = db.execute(
            "UPDATE conversations SET title=?, updated_at=? WHERE id=?",
            (new_title, _now(), conversation_id),
        ).rowcount
    return get_conversation(conversation_id) if changed else None


def search_conversations(query: str, limit: int = 20) -> list[dict]:
    """Private local full-text search. Never invokes an inference provider.

    Bound the query and match terms. SQLite MATCH is constructed from quoted
    lexical tokens, not arbitrary FTS operators supplied by the caller.
    """
    if not 2 <= len(query) <= 200 or not 1 <= limit <= 50:
        raise HTTPException(422, "Search must be 2-200 characters with limit 1-50")
    tokens = re.findall(r"[^\W_]{2,}", query, re.UNICODE)[:8]
    if not tokens:
        return []
    expression = " OR ".join('"' + term + '"*' for term in tokens)
    escaped = query.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    with _connection() as db:
        rows = db.execute("""
            SELECT c.id, c.title, c.created_at, c.updated_at,
                   COUNT(m.id) AS message_count
              FROM conversations c
              LEFT JOIN messages m ON m.conversation_id=c.id
             WHERE lower(c.title) LIKE ? ESCAPE '\\'
                OR c.id IN (
                    SELECT DISTINCT linked.conversation_id
                      FROM message_fts
                      JOIN messages linked ON linked.rowid=message_fts.rowid
                     WHERE message_fts MATCH ?
                )
             GROUP BY c.id
             ORDER BY c.updated_at DESC, c.id ASC LIMIT ?
        """, (f"%{escaped}%", expression, limit)).fetchall()
    return [dict(row) for row in rows]


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


def _consent_retention_days() -> int:
    try:
        days = int(os.getenv("GOREECLOUD_AI_CONSENT_RECEIPT_RETENTION_DAYS", "30"))
        if not 1 <= days <= 365:
            raise ValueError("days outside allowed range")
        return days
    except ValueError as exc:
        raise HTTPException(503, "Invalid cloud consent receipt retention configuration") from exc


def admit_cloud_call(kind: str, *, approved: bool = False) -> None:
    """Atomic cloud admission and content-free consent receipt.

    This proves only admission after approval, not actual network transfer,
    generation, billing, provider use, or user identity.
    """
    if approved is not True:
        raise HTTPException(403, "Explicit cloud-processing approval required")
    if kind not in ("chat", "chat-stream", "image", "agent-plan", "research"):
        raise HTTPException(422, "Invalid cloud request kind")
    limit = _daily_limit()
    keep = _consent_retention_days()
    now = datetime.now(UTC)
    day = now.date().isoformat()
    cutoff = (now - timedelta(days=14)).date().isoformat()
    receipts_cutoff = (now - timedelta(days=keep)).isoformat()
    request_id = str(uuid.uuid4())
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        admitted = db.execute(
            "SELECT COUNT(*) FROM paid_call_admissions WHERE day=?", (day,)).fetchone()[0]
        if admitted >= limit:
            raise HTTPException(429, "Daily external-provider request limit reached")
        db.execute("INSERT INTO paid_call_admissions VALUES (?, ?, ?)", (request_id, day, kind))
        db.execute(
            "INSERT INTO cloud_consent_receipts VALUES (?, ?, ?, ?)",
            (request_id, now.isoformat(), kind,
             "paid-image-approval" if kind == "image" else "cloud-processing-consent"),
        )
        db.execute("DELETE FROM paid_call_admissions WHERE day < ?", (cutoff,))
        db.execute("DELETE FROM cloud_consent_receipts WHERE created_at < ?", (receipts_cutoff,))


def list_cloud_consent_receipts(limit: int = 100) -> dict:
    if not 1 <= limit <= 200:
        raise HTTPException(422, "Consent receipt limit must be 1-200")
    cutoff = (datetime.now(UTC) - timedelta(days=_consent_retention_days())).isoformat()
    with _connection() as db:
        db.execute("DELETE FROM cloud_consent_receipts WHERE created_at < ?", (cutoff,))
        rows = db.execute(
            "SELECT id,created_at,kind,approval FROM cloud_consent_receipts "
            "ORDER BY created_at DESC LIMIT ?", (limit,),
        )
        result = [dict(row) for row in rows]
    return {"receipts": result,
            "note": "Cloud call admissions after explicit approval; not proof of transfer or billing."}


def clear_cloud_consent_receipts() -> dict:
    with _connection() as db:
        count = db.execute("DELETE FROM cloud_consent_receipts").rowcount
    return {"deleted_receipts": count,
            "note": "Consent admission metadata cleared; paid request quota is unchanged."}



def conversation_retention_days() -> int:
    """0 disables expiration; deletions require a separate owner approval."""
    try:
        days = int(os.getenv("GOREECLOUD_AI_CONVERSATION_RETENTION_DAYS", "0"))
        if not 0 <= days <= 3650:
            raise ValueError("days out of range")
        return days
    except ValueError as exc:
        raise HTTPException(503, "Invalid conversation retention policy") from exc


def purge_expired_conversations() -> dict:
    """Delete old opt-in snapshots only. SQLite pages and backups are not wiped."""
    days = conversation_retention_days()
    if days == 0:
        raise HTTPException(409, "Conversation retention cleanup is not configured")
    cutoff = (datetime.now(UTC) - timedelta(days=days)).isoformat()
    with _connection() as db:
        count = db.execute("DELETE FROM conversations WHERE updated_at < ?", (cutoff,)).rowcount
    return {"deleted_conversations": count, "cutoff_utc": cutoff,
            "note": "Live rows removed; encrypted backup copies and SQLite pages may retain history."}
