"""Opt-in SQLCipher storage adapter; never select a backend based on file content.

The default remains plain SQLite for existing developer databases. To encrypt
the full database and FTS indexes, use the deliberate offline migrate command,
then set mode, key and path atomically in a private service configuration.
"""
import base64
import binascii
import os
import sqlite3
import stat
from pathlib import Path

from fastapi import HTTPException

SQLITE_HEADER = b"SQLite format 3\x00"


def database_mode() -> str:
    mode = os.getenv("GOREECLOUD_AI_DB_MODE", "plaintext")
    if mode not in ("plaintext", "sqlcipher"):
        raise HTTPException(503, "Invalid database encryption mode")
    return mode


def _sqlcipher_driver():
    try:
        import sqlcipher3
    except ImportError as exc:
        raise HTTPException(503, "SQLCipher backend is not installed") from exc
    return sqlcipher3


def _database_key() -> bytes:
    try:
        supplied = os.environ["GOREECLOUD_AI_DB_KEY"]
        key = base64.b64decode(supplied, validate=True)
        if len(key) != 32:
            raise ValueError("Key length")
    except (KeyError, ValueError, binascii.Error) as exc:
        raise HTTPException(503, "A valid external 32-byte database key is required") from exc
    return key


def _check_path(path: Path, mode: str, *, create: bool) -> None:
    if path.is_symlink():
        raise HTTPException(503, "Database path must not be a symlink")
    if path.exists():
        if not path.is_file():
            raise HTTPException(503, "Database path is not a regular file")
        if path.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            if mode == "sqlcipher":
                raise HTTPException(503, "Encrypted database file has unsafe permissions")
            # Retain the legacy plaintext behavior of restricting files to 0600.
            path.chmod(0o600)
        with path.open("rb") as stream:
            first = stream.read(len(SQLITE_HEADER))
        # A just-created SQLite file may still have a partial header while
        # another connection is initializing it. Only classify complete headers;
        # the DB engine will enforce locking and key checks on concurrent opens.
        if (len(first) == len(SQLITE_HEADER)
                and first.startswith(SQLITE_HEADER) != (mode == "plaintext")):
            raise HTTPException(503, "Database encryption mode and file format disagree")
    elif create:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags, 0o600)
        except FileExistsError:
            # Another authorized request created the private file concurrently.
            # Verify its real path/mode and leave schema/key locking to SQLite.
            _check_path(path, mode, create=False)
        else:
            os.close(fd)
    else:
        raise HTTPException(503, "Database does not exist")


def connect(path: Path, *, create: bool = True):
    """Open selected backend, checking key before any schema initialization."""
    mode = database_mode()
    path = path.expanduser()
    if mode == "sqlcipher":
        key = _database_key()
        driver = _sqlcipher_driver()
    else:
        driver = sqlite3
        key = None
    _check_path(path, mode, create=create)
    db = driver.connect(str(path), timeout=10)
    try:
        if key is not None:
            db.execute("PRAGMA key = \"x'" + key.hex() + "'\"")
            # Fail before any CREATE TABLE; a bad key never destroys old data.
            version = db.execute("PRAGMA cipher_version").fetchone()
            if not version or not version[0]:
                raise HTTPException(503, "SQLCipher encryption support is unavailable")
            db.execute("SELECT count(*) FROM sqlite_master").fetchone()
            db.execute("PRAGMA cipher_memory_security=ON")
            db.execute("PRAGMA temp_store=MEMORY")
        else:
            db.execute("SELECT count(*) FROM sqlite_master").fetchone()
        db.execute("PRAGMA secure_delete=ON")
        return db
    except Exception as exc:
        db.close()
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(503, "Database key or format validation failed") from exc



def row_factory():
    return _sqlcipher_driver().Row if database_mode() == "sqlcipher" else sqlite3.Row
