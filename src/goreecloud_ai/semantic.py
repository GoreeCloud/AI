"""Explicit local semantic retrieval using bounded Ollama embeddings and SQLite.

This is a small-document reference backend, not a production vector database.
"""
from contextlib import contextmanager
import json
import math
from pathlib import Path
import sqlite3

MAX_SEARCH_CHUNKS = 4096


def chunk_text(text: str, width: int = 800, overlap: int = 80) -> list[str]:
    """Bound chunks with deterministic overlap; never silently truncate content."""
    if not 0 < overlap < width or width > 1600:
        raise ValueError("Invalid chunk parameters")
    chunks = [text[i:i + width] for i in range(0, len(text), width - overlap)]
    chunks = [part for part in chunks if part.strip()]
    if not chunks or len(chunks) > 80:
        raise ValueError("Document is empty or exceeds 80 embedding chunks")
    return chunks


def clean_vector(values: list[float]) -> list[float]:
    if not isinstance(values, list) or not 1 <= len(values) <= 4096:
        raise ValueError("Embedding vector has invalid dimensions")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in values):
        raise ValueError("Embedding vector contains nonnumeric elements")
    vector = [float(v) for v in values]
    if not all(math.isfinite(v) for v in vector) or not any(v != 0 for v in vector):
        raise ValueError("Embedding vector is not finite and nonzero")
    return vector


def cosine(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right):
        return None
    norm_left = math.hypot(*left)
    norm_right = math.hypot(*right)
    if not math.isfinite(norm_left) or not math.isfinite(norm_right) or norm_left == 0 or norm_right == 0:
        return None
    return math.fsum((a / norm_left) * (b / norm_right) for a, b in zip(left, right))


class SemanticIndex:
    def __init__(self, database_path: str):
        self.path = str(Path(database_path).expanduser())
        with self.connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS semantic_chunks (
                    document_id TEXT NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
                    model TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    excerpt TEXT NOT NULL,
                    vector_json TEXT NOT NULL,
                    PRIMARY KEY (document_id, model, chunk_index)
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_semantic_model ON semantic_chunks(model)")

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

    def save(self, document_id: str, model: str, chunks: list[str], vectors: list[list[float]]) -> int:
        if not chunks or len(chunks) > 80 or len(chunks) != len(vectors):
            raise ValueError("Embedding batch count mismatch")
        clean = [clean_vector(v) for v in vectors]
        if len({len(v) for v in clean}) != 1:
            raise ValueError("Embedding vectors have inconsistent dimensions")
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM knowledge_documents WHERE id=?", (document_id,)).fetchone() is None:
                raise KeyError("Document was deleted before indexing completed")
            db.execute("DELETE FROM semantic_chunks WHERE document_id=? AND model=?", (document_id, model))
            for index, (chunk, vector) in enumerate(zip(chunks, clean)):
                db.execute(
                    "INSERT INTO semantic_chunks (document_id,model,chunk_index,excerpt,vector_json) VALUES (?,?,?,?,?)",
                    (document_id, model, index, chunk, json.dumps(vector, separators=(",", ":"))),
                )
        return len(chunks)

    def indexed_count(self, model: str) -> int:
        with self.connect() as db:
            return db.execute("SELECT COUNT(*) FROM semantic_chunks WHERE model=?", (model,)).fetchone()[0]

    def status(self) -> list[dict]:
        """Return bounded index counts only; never expose stored text or vectors."""
        with self.connect() as db:
            rows = db.execute(
                """SELECT model, COUNT(*) AS chunks, COUNT(DISTINCT document_id) AS documents
                   FROM semantic_chunks GROUP BY model ORDER BY model LIMIT 100"""
            ).fetchall()
        return [dict(row) for row in rows]

    def search(self, query_vector: list[float], model: str, limit: int = 3) -> list[dict]:
        query = clean_vector(query_vector)
        with self.connect() as db:
            rows = db.execute(
                """SELECT s.document_id, d.title, s.excerpt, s.vector_json
                   FROM semantic_chunks AS s
                   JOIN knowledge_documents AS d ON d.id = s.document_id
                   WHERE s.model=? ORDER BY s.document_id,s.chunk_index LIMIT ?""",
                (model,MAX_SEARCH_CHUNKS+1),
            ).fetchall()
        if len(rows) > MAX_SEARCH_CHUNKS:
            raise ValueError("Semantic index exceeds local search capacity; no partial results returned")
        best: dict[str, dict] = {}
        for row in rows:
            try:
                vector = clean_vector(json.loads(row["vector_json"]))
            except (ValueError, TypeError) as exc:
                raise ValueError("Indexed vector is corrupt; rebuild the semantic index") from exc
            if len(vector) != len(query):
                raise ValueError("Embedding dimensions do not match; rebuild the semantic index")
            score = cosine(query, vector)
            if score is None or score <= 0:
                continue
            match = {
                "id": row["document_id"], "title": row["title"],
                "excerpt": row["excerpt"][:700], "score": round(score, 6),
                "retrieval": "semantic", "model": model,
            }
            if match["id"] not in best or score > best[match["id"]]["score"]:
                best[match["id"]] = match
        return sorted(best.values(), key=lambda row: (-row["score"], row["title"], row["id"]))[:max(0, min(limit, 10))]
