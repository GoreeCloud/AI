"""Optional Wardveil-preview Linux Bubblewrap boundary for document imports.

No permissions are inherited beyond read-only Python runtime + parser code,
sandbox-local /tmp,/proc,/dev, anonymous stdin/stdout and no network namespace.
Do not treat this as certified isolation or a production policy engine.
"""
import os
import shutil
import stat
import sys
from pathlib import Path

from fastapi import HTTPException

SANDBOX_MODES = ("process", "bwrap")


def import_mode() -> str:
    mode = os.getenv("GOREECLOUD_AI_IMPORT_ISOLATION", "process")
    if mode not in SANDBOX_MODES:
        raise HTTPException(503, "Invalid document import isolation mode")
    return mode


def _trusted_bwrap_binary() -> str:
    raw = os.getenv("GOREECLOUD_AI_BWRAP_PATH", "") or shutil.which("bwrap")
    if not raw:
        raise HTTPException(503, "Required Bubblewrap sandbox is not installed")
    try:
        path = Path(raw)
        if not path.is_absolute() or path.is_symlink():
            raise ValueError("Unsupported sandbox binary location")
        resolved = path.resolve(strict=True)
        st = resolved.stat()
        if (not resolved.is_file() or st.st_uid != 0
                or st.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
                or not os.access(resolved, os.X_OK)):
            raise ValueError("Sandbox binary has unsafe permissions")
    except (OSError, ValueError) as exc:
        raise HTTPException(503, "Sandbox binary failed integrity checks") from exc
    return str(resolved)


def parser_command(worker: Path, suffix: str) -> list[str]:
    if suffix not in ("txt", "md", "pdf", "docx"):
        raise HTTPException(415, "Unsupported document type")
    if import_mode() == "process":
        return [sys.executable, "-I", str(worker), suffix]
    binary = _trusted_bwrap_binary()
    # Only a trusted immutable-ish Python runtime and the worker script are
    # visible; do NOT bind the project root, real HOME, /etc, host /tmp or data.
    # The runtime is read-only and must be deployed in a non-world-writable path.
    prefix = Path(sys.prefix).resolve()
    if sys.prefix != sys.base_prefix:
        if not (prefix / "pyvenv.cfg").is_file() or not (prefix / "bin/python").exists():
            raise HTTPException(503, "Sandbox requires a conventional Python venv")
        interpreter = "/goree-runtime/bin/python"
    else:
        interpreter = sys.executable
        if not interpreter.startswith(("/usr/", "/bin/")):
            raise HTTPException(503, "Sandbox requires a supported system Python")
    args = [
        binary, "--unshare-all", "--die-with-parent", "--new-session",
        "--clearenv", "--setenv", "LANG", "C.UTF-8",
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
        "--setenv", "HOME", "/nonexistent",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind-try", "/lib", "/lib",
        "--ro-bind-try", "/lib64", "/lib64",
        "--ro-bind-try", "/etc/ld.so.cache", "/etc/ld.so.cache",
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--dir", "/app",
        "--ro-bind", str(worker.resolve(strict=True)), "/app/extract_worker.py",
    ]
    # GitHub Actions setup-python can install its interpreter under
    # /opt/hostedtoolcache/Python rather than /usr. Mount only that verified
    # public toolchain prefix, never all of /opt, host HOME or project files.
    base = Path(sys.base_prefix).resolve(strict=True)
    if not base.is_relative_to(Path("/usr")):
        if not base.is_relative_to(Path("/opt/hostedtoolcache/Python")):
            raise HTTPException(503, "Unsupported Python base installation for sandbox")
        for parent in reversed(base.parents):
            if parent != Path("/"):
                args.extend(["--dir", str(parent)])
        args.extend(["--ro-bind", str(base), str(base)])
    if sys.prefix != sys.base_prefix:
        args.extend(["--ro-bind", str(prefix), "/goree-runtime"])
    args.extend(["--chdir", "/", "--", interpreter, "-I",
                 "/app/extract_worker.py", suffix])
    return args
