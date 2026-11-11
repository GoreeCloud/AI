"""Local keyword knowledge retrieval. No cloud embeddings or model downloads."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
from uuid import uuid4

_STOPWORDS = frozenset({"what", "where", "when", "which", "who", "with", "that", "this", "from", "your", "about", "into", "have", "does", "tell", "explain", "please", "could", "would", "should"})


class KnowledgeStore:
    def __init__(self, db_path: str):
        self.path = str(Path(db_path).expanduser())
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
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

    def add(self, title: str, body: str) -> dict:
        document = {
            "id": str(uuid4()),
            "title": title.strip(),
            "body": body,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self.connect() as db:
            db.execute("INSERT INTO knowledge_documents (id,title,body,created_at) VALUES (:id,:title,:body,:created_at)", document)
        return {k: v for k, v in document.items() if k != "body"}

    def list_documents(self) -> list[dict]:
        with self.connect() as db:
            rows = db.execute("SELECT id,title,created_at FROM knowledge_documents ORDER BY created_at DESC LIMIT 200").fetchall()
        return [dict(row) for row in rows]


    def get_document(self, document_id: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT id,title,body,created_at FROM knowledge_documents WHERE id=?", (document_id,)).fetchone()
        return dict(row) if row else None

    def delete(self, document_id: str) -> bool:
        with self.connect() as db:
            return db.execute("DELETE FROM knowledge_documents WHERE id=?", (document_id,)).rowcount > 0

    def search(self, query: str, limit: int = 3) -> list[dict]:
        """Rank bounded local documents by keyword coverage, not semantic similarity."""
        terms = [t for t in dict.fromkeys(re.findall(r"[a-zA-Z0-9_]{3,}", query.lower())) if t not in _STOPWORDS][:12]
        if not terms:
            return []
        with self.connect() as db:
            rows = db.execute("SELECT id,title,body FROM knowledge_documents LIMIT 2000").fetchall()
        results = []
        for doc in rows:
            title = doc["title"].lower()
            body = doc["body"].lower()
            matches = [t for t in terms if t in title or t in body]
            if not matches:
                continue
            score = len(matches) + 2 * sum(t in title for t in matches)
            positions = [body.find(t) for t in matches if t in body]
            start = max(0, min(positions) - 100) if positions else 0
            excerpt = doc["body"][start:start + 700]
            results.append({"id": doc["id"], "title": doc["title"], "excerpt": excerpt, "score": score})
        results.sort(key=lambda x: (-x["score"], x["title"].lower(), x["id"]))
        return results[:max(0, min(limit, 10))]
