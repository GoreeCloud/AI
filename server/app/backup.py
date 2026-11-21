"""Offline, encrypted SQLite snapshots with authenticated restore.

Operator CLI only; never exposes the encryption key through an HTTP route.
Use a private 32-byte base64 key from GOREECLOUD_AI_BACKUP_KEY. Loss of this
key permanently prevents restore. A snapshot is not a production backup plan.
"""
import argparse
import base64
import binascii
import os
import sqlite3
import stat
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"GCAI-BACKUP-v1\x00"
MAX_BYTES = 256 * 1024 * 1024


def _key() -> bytes:
    try:
        encoded = os.environ["GOREECLOUD_AI_BACKUP_KEY"]
        decoded = base64.b64decode(encoded, validate=True)
        if len(decoded) != 32:
            raise ValueError("Expected a 256-bit backup encryption key")
        return decoded
    except (KeyError, ValueError, binascii.Error) as exc:
        raise ValueError("Set a valid 32-byte base64 GOREECLOUD_AI_BACKUP_KEY") from exc


def _private_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir() or path.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise ValueError("Directory must not be a symlink or group/world-writable")


def _temporary(path: Path) -> Path:
    fd, name = tempfile.mkstemp(prefix=".gcai-", dir=str(path))
    os.close(fd)
    os.chmod(name, 0o600)
    return Path(name)


def _sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_exclusive(destination: Path, contents: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(destination, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(contents)
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    _sync_directory(destination.parent)


def backup(database: Path, destination: Path) -> None:
    _private_directory(destination.parent)
    if not database.is_file() or database.is_symlink():
        raise ValueError("Database file is missing or untrusted")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Backup output already exists")
    snapshot = _temporary(destination.parent)
    try:
        with sqlite3.connect(database) as source, sqlite3.connect(snapshot) as target:
            source.backup(target)
        data = snapshot.read_bytes()
        if len(data) > MAX_BYTES:
            raise ValueError("Snapshot exceeds 256 MiB memory-safe limit")
        if not data.startswith(b"SQLite format 3\x00"):
            raise ValueError("Source is not a SQLite database")
        nonce = os.urandom(12)
        ciphertext = AESGCM(_key()).encrypt(nonce, data, MAGIC)
        _write_exclusive(destination, MAGIC + nonce + ciphertext)
    finally:
        snapshot.unlink(missing_ok=True)


def restore(source: Path, destination: Path) -> None:
    _private_directory(destination.parent)
    if not source.is_file() or source.is_symlink():
        raise ValueError("Encrypted backup is missing or untrusted")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Restore target already exists; no overwrites are allowed")
    if source.stat().st_size > MAX_BYTES + 128:
        raise ValueError("Encrypted backup exceeds supported limit")
    payload = source.read_bytes()
    if not payload.startswith(MAGIC) or len(payload) < len(MAGIC) + 12 + 16:
        raise ValueError("Backup format is invalid")
    nonce = payload[len(MAGIC):len(MAGIC) + 12]
    plaintext = AESGCM(_key()).decrypt(nonce, payload[len(MAGIC) + 12:], MAGIC)
    if not plaintext.startswith(b"SQLite format 3\x00"):
        raise ValueError("Decrypted backup is not SQLite")
    snapshot = _temporary(destination.parent)
    try:
        _write_existing_private(snapshot, plaintext)
        with sqlite3.connect(f"file:{snapshot}?mode=ro", uri=True) as db:
            if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Restored database failed integrity check")
            if "documents" not in {r[0] for r in db.execute("SELECT name FROM sqlite_master")}:
                raise ValueError("Restored file is not a GoreeCloud AI database")
        # Atomic exclusive publish, without clobbering an existing target.
        os.link(snapshot, destination, follow_symlinks=False)
        _sync_directory(destination.parent)
    finally:
        snapshot.unlink(missing_ok=True)


def _write_existing_private(path: Path, contents: bytes) -> None:
    with path.open("wb") as output:
        output.write(contents)
        output.flush()
        os.fsync(output.fileno())
    os.chmod(path, 0o600)


def main() -> None:
    parser = argparse.ArgumentParser(description="Encrypted, offline GoreeCloud AI SQLite backup")
    command = parser.add_subparsers(dest="command", required=True)
    for name in ("backup", "restore"):
        p = command.add_parser(name)
        p.add_argument("--source", type=Path, required=True)
        p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "backup":
            backup(args.source.expanduser(), args.output.expanduser())
        else:
            restore(args.source.expanduser(), args.output.expanduser())
    except Exception as exc:
        # Deliberately do not report paths, keys, ciphertext or private content.
        raise SystemExit(f"Encrypted {args.command} failed: {type(exc).__name__}") from None
    print(f"Encrypted {args.command} verified. Protect the external key and offline copy.")


if __name__ == "__main__":
    main()
