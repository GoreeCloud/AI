"""Wardveil-preview Bubblewrap import sandbox contract and synthetic live tests."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

from app import import_sandbox
from app.main import parse_document_isolated


def _require_working_bwrap():
    binary = shutil.which("bwrap")
    if not binary:
        pytest.skip("Bubblewrap binary is absent on this runner")
    smoke = subprocess.run([
        binary, "--unshare-all", "--die-with-parent", "--new-session",
        "--clearenv", "--ro-bind", "/usr", "/usr",
        "--ro-bind-try", "/lib", "/lib",
        "--ro-bind-try", "/lib64", "/lib64",
        "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp",
        "--", "/usr/bin/true",
    ], capture_output=True, timeout=6, env={"LANG": "C.UTF-8"})
    if smoke.returncode:
        explanation = smoke.stderr.decode("utf-8", errors="replace").lower()
        if any(marker in explanation for marker in (
            "operation not permitted", "permission denied", "user namespaces",
            "no permissions to create new namespace",
            "creating new namespace failed",
        )):
            pytest.skip("Runner kernel denies unprivileged namespace creation")
        pytest.fail("Bubblewrap installed but namespace smoke check failed")
    return binary


@pytest.mark.parametrize("name", ["", "best", "bwrap ", "disabled"])
def test_invalid_mode_fails_closed(monkeypatch, name):
    monkeypatch.setenv("GOREECLOUD_AI_IMPORT_ISOLATION", name)
    with pytest.raises(HTTPException) as exc:
        import_sandbox.import_mode()
    assert exc.value.status_code == 503


def test_process_mode_backward_compatible(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_IMPORT_ISOLATION", "process")
    command = import_sandbox.parser_command(Path("/tmp/does-not-need-to-exist.py"), "txt")
    assert command == [sys.executable, "-I", "/tmp/does-not-need-to-exist.py", "txt"]


def test_bwrap_mode_fails_closed_without_installed_binary(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_IMPORT_ISOLATION", "bwrap")
    monkeypatch.setenv("GOREECLOUD_AI_BWRAP_PATH", "/definitely/no/bwrap")
    with pytest.raises(HTTPException) as exc:
        import_sandbox.parser_command(Path("/tmp/anything.py"), "txt")
    assert exc.value.status_code == 503


def test_sandbox_command_excludes_host_secrets(monkeypatch):
    exe = shutil.which("bwrap")
    if not exe:
        pytest.skip("Bubblewrap binary is not installed")
    monkeypatch.setenv("GOREECLOUD_AI_IMPORT_ISOLATION", "bwrap")
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-secret-never-on-command-line")
    worker = Path(__file__).resolve().parents[1] / "app/extract_worker.py"
    cmd = import_sandbox.parser_command(worker, "docx")
    assert "--unshare-all" in cmd and "--clearenv" in cmd
    assert "--ro-bind" in cmd and "--tmpfs" in cmd
    assert cmd[-1] == "docx"
    assert "synthetic-secret-never-on-command-line" not in str(cmd)
    assert "/home/" not in " ".join(cmd[:13])
    assert "/app/extract_worker.py" in cmd


@pytest.mark.asyncio
async def test_real_opt_in_sandbox_extracts_synthetic_text(monkeypatch):
    _require_working_bwrap()
    monkeypatch.setenv("GOREECLOUD_AI_IMPORT_ISOLATION", "bwrap")
    result = await parse_document_isolated("A synthetic résumé".encode(), "txt")
    assert result == {"text": "A synthetic résumé", "truncated": False}


def test_real_sandbox_denies_host_path_and_network(tmp_path, monkeypatch):
    _require_working_bwrap()
    marker = tmp_path / "synthetic-private-host-note.txt"
    marker.write_text("known dummy", encoding="utf-8")
    probe = tmp_path / "probe.py"
    probe.write_text(
        "import os, json, pathlib, sys\n"
        "path=sys.argv[2]\n"
        "print(json.dumps({'exists': pathlib.Path(path).exists(),"
        " 'key': 'OPENROUTER_API_KEY' in os.environ,"
        " 'routes': pathlib.Path('/proc/net/route').read_text().splitlines()[1:]}))\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "synthetic-not-for-child")
    monkeypatch.setenv("GOREECLOUD_AI_IMPORT_ISOLATION", "bwrap")
    cmd = import_sandbox.parser_command(probe, "txt") + [str(marker)]
    result = subprocess.run(cmd, capture_output=True, timeout=8, check=True, text=True)
    import json
    payload = json.loads(result.stdout)
    assert payload == {"exists": False, "key": False, "routes": []}


def test_bwrap_rejects_unknown_suffix(monkeypatch):
    monkeypatch.setenv("GOREECLOUD_AI_IMPORT_ISOLATION", "bwrap")
    with pytest.raises(HTTPException) as exc:
        import_sandbox.parser_command(Path("/tmp/w.py"), "../secrets")
    assert exc.value.status_code == 415


@pytest.mark.asyncio
async def test_requested_sandbox_execution_failure_never_falls_back(monkeypatch):
    from app import main as api
    monkeypatch.setenv("GOREECLOUD_AI_IMPORT_ISOLATION", "bwrap")
    class FailedSandbox:
        returncode = 1
        async def communicate(self, _contents):
            return b"", b""
    calls = []
    async def fake_spawn(*args, **_kwargs):
        calls.append(args)
        return FailedSandbox()
    monkeypatch.setattr(api.asyncio, "create_subprocess_exec", fake_spawn)
    with pytest.raises(HTTPException) as exc:
        await api.parse_document_isolated(b"synthetic", "txt")
    assert exc.value.status_code == 503
    assert len(calls) == 1
    assert calls[0][0].endswith("/bwrap")
