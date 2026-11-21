"""Offline source-preserving SQLCipher key rotation.

Only for a trusted stopped API. The old encrypted file and existing backups
remain untouched. No key is accepted in CLI arguments or printed.
"""
import argparse
import base64
import binascii
import hmac
import os
import stat
import tempfile
from contextlib import closing
from pathlib import Path

from fastapi import HTTPException

from . import database


def _next_key() -> bytes:
    try:
        encoded = os.environ["GOREECLOUD_AI_NEW_DB_KEY"]
        key = base64.b64decode(encoded, validate=True)
        if len(key) != 32:
            raise ValueError("New key must have 32 bytes")
        return key
    except (KeyError, ValueError, binascii.Error) as exc:
        raise ValueError("A valid external next database key is required") from exc


def rotate(source: Path, destination: Path) -> None:
    if database.database_mode() != "sqlcipher":
        raise ValueError("Key rotation requires SQLCipher storage mode")
    source = source.expanduser()
    destination = destination.expanduser()
    current = database._database_key()
    next_key = _next_key()
    if hmac.compare_digest(current, next_key):
        raise ValueError("Next key must be distinct from the current key")
    if not source.is_file() or source.is_symlink():
        raise ValueError("Source must be an existing regular encrypted database")
    if source.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ValueError("Source database permissions are too broad")
    if (source.parent / (source.name + "-wal")).exists():
        raise ValueError("Source has a WAL sidecar; stop and checkpoint the API")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Target database already exists")
    destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (destination.parent.is_symlink() or not destination.parent.is_dir()
            or destination.parent.stat().st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
        raise ValueError("Target directory is not private")
    if source.resolve() == destination.resolve():
        raise ValueError("New database must use a separate destination")

    driver = database._sqlcipher_driver()
    fd, filename = tempfile.mkstemp(prefix=".gcai-rotate-", dir=str(destination.parent))
    os.close(fd)
    scratch = Path(filename)
    try:
        # Validating the current key happens before the new file export.
        with closing(database.connect(source, create=False)) as connection:
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Source database integrity check failed")
            if "documents" not in {
                row[0] for row in connection.execute("SELECT name FROM sqlite_master")
            }:
                raise ValueError("Not a GoreeCloud AI database")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            connection.execute(
                "ATTACH DATABASE ? AS rotated KEY ?",
                (str(scratch), "x'" + next_key.hex() + "'"),
            )
            try:
                connection.execute("SELECT sqlcipher_export('rotated')").fetchone()
                connection.execute("PRAGMA rotated.user_version=" + str(int(version)))
            finally:
                connection.execute("DETACH DATABASE rotated")
        with closing(driver.connect(str(scratch))) as target:
            target.execute("PRAGMA key = \"x'" + next_key.hex() + "'\"")
            if target.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Rotated database integrity check failed")
            if target.execute("PRAGMA user_version").fetchone()[0] != version:
                raise ValueError("Schema version changed during rotation")
            if "documents" not in {
                row[0] for row in target.execute("SELECT name FROM sqlite_master")
            }:
                raise ValueError("Rotated database schema is invalid")
        with scratch.open("rb") as stream:
            if stream.read(len(database.SQLITE_HEADER)) == database.SQLITE_HEADER:
                raise ValueError("Rotated database unexpectedly plaintext")
            os.fsync(stream.fileno())
        scratch.chmod(0o600)
        os.link(scratch, destination, follow_symlinks=False)
        folder_fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(folder_fd)
        finally:
            os.close(folder_fd)
    finally:
        scratch.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rotate GoreeCloud AI SQLCipher key offline into a NEW database"
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        rotate(args.source, args.output)
    except Exception as exc:
        # Do not disclose key data, host paths, records or stack traces.
        name = "ConfigurationError" if isinstance(exc, HTTPException) else type(exc).__name__
        raise SystemExit("SQLCipher offline key rotation failed: " + name) from None
    print("Encrypted database verified with next key; original preserved.")


if __name__ == "__main__":
    main()
