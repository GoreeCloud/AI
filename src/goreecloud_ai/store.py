"""Local SQLite persistence; no external database or cloud dependency."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: str):
        self.path = str(Path(path).expanduser())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS chats (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    chat_id TEXT NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
                    role TEXT NOT NULL CHECK(role IN ('user','assistant')),
                    content TEXT NOT NULL,
                    model TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_messages_chat ON messages(chat_id, created_at);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=5000")
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def list_chats(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT id,title,created_at FROM chats ORDER BY created_at DESC LIMIT 200").fetchall()
            return [dict(row) for row in rows]

    def create_chat(self, title: str) -> dict:
        chat = {"id": str(uuid4()), "title": title, "created_at": utc_now()}
        with self.connect() as db:
            db.execute("INSERT INTO chats (id,title,created_at) VALUES (:id,:title,:created_at)", chat)
        return chat

    def get_chat(self, chat_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT id,title,created_at FROM chats WHERE id=?", (chat_id,)).fetchone()
            if not row:
                return None
            messages = db.execute(
                "SELECT id,role,content,model,created_at FROM messages WHERE chat_id=? ORDER BY created_at ASC, rowid ASC",
                (chat_id,),
            ).fetchall()
        return {**dict(row), "messages": [dict(m) for m in messages]}

    def delete_chat(self, chat_id: str) -> bool:
        with self.connect() as db:
            result = db.execute("DELETE FROM chats WHERE id=?", (chat_id,))
            return result.rowcount > 0

    def add_exchange(self, chat_id: str, user_text: str, assistant_text: str, model: str) -> None:
        now = utc_now()
        with self.connect() as db:
            db.execute("UPDATE chats SET title=? WHERE id=? AND title='New conversation'", (user_text[:72], chat_id))
            db.execute(
                "INSERT INTO messages (id,chat_id,role,content,model,created_at) VALUES (?,?,?,?,?,?)",
                (str(uuid4()), chat_id, "user", user_text, None, now),
            )
            db.execute(
                "INSERT INTO messages (id,chat_id,role,content,model,created_at) VALUES (?,?,?,?,?,?)",
                (str(uuid4()), chat_id, "assistant", assistant_text, model, now),
            )
