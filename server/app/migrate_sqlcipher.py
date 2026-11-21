"""Offline, non-overwriting conversion from legacy SQLite to SQLCipher.

Run ONLY with the API stopped and after a validated offline backup. The source
file is never removed, modified, or automatically used as the new destination.
"""
import argparse
import os
import stat
import tempfile
from pathlib import Path

from . import database


def migrate(source: Path, destination: Path) -> None:
    source, destination = source.expanduser(), destination.expanduser()
    if not source.is_file() or source.is_symlink() or source.stat().st_size == 0:
        raise ValueError("Source is not an existing regular SQLite database")
    if source.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        raise ValueError("Source file has unsafe permissions")
    with source.open("rb") as raw:
        if raw.read(len(database.SQLITE_HEADER)) != database.SQLITE_HEADER:
            raise ValueError("Source must be legacy plaintext SQLite")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Destination must not exist")
    if (source.parent / (source.name + "-wal")).exists():
        raise ValueError("Source has a WAL sidecar; stop the API and checkpoint first")
    destination.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if destination.parent.is_symlink() or destination.parent.stat().st_mode & (
            stat.S_IWGRP | stat.S_IWOTH):
        raise ValueError("Destination folder must be private")
    key = database._database_key()
    driver = database._sqlcipher_driver()

    fd, filename = tempfile.mkstemp(prefix=".gcai-migrate-", dir=str(destination.parent))
    os.close(fd)
    scratch = Path(filename)
    try:
        connection = driver.connect(str(source), timeout=10)
        try:
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Legacy database is not consistent")
            if "documents" not in {
                row[0] for row in connection.execute("SELECT name FROM sqlite_master")
            }:
                raise ValueError("Source is not a GoreeCloud AI database")
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            # The path is a private file generated here, never remote/user SQL.
            # Key is available only in process memory, not logs or CLI arguments.
            connection.execute(
                "ATTACH DATABASE ? AS encrypted KEY ?", (str(scratch), "x'" + key.hex() + "'")
            )
            try:
                connection.execute("SELECT sqlcipher_export('encrypted')").fetchone()
                connection.execute("PRAGMA encrypted.user_version=" + str(int(version)))
            finally:
                connection.execute("DETACH DATABASE encrypted")
        finally:
            connection.close()
        with driver.connect(str(scratch)) as check:
            check.execute("PRAGMA key = \"x'" + key.hex() + "'\"")
            if check.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise ValueError("Encrypted migration integrity check failed")
            if check.execute("PRAGMA user_version").fetchone()[0] != version:
                raise ValueError("Migration did not preserve schema version")
        with scratch.open("rb") as raw:
            if raw.read(len(database.SQLITE_HEADER)) == database.SQLITE_HEADER:
                raise ValueError("Migration did not encrypt destination")
        scratch.chmod(0o600)
        with scratch.open("rb") as final:
            os.fsync(final.fileno())
        os.link(scratch, destination, follow_symlinks=False)
        fd = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        scratch.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline GoreeCloud AI SQLite to SQLCipher conversion (keeps original)"
    )
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        migrate(args.source, args.output)
    except Exception as exc:
        # Never print paths, keys, old content or tracebacks in CLI errors.
        raise SystemExit("Offline encryption migration failed: " + type(exc).__name__) from None
    print("Encrypted database verified at new private destination; original preserved.")


if __name__ == "__main__":
    main()
