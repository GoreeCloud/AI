"""Wardveil-preview Bubblewrap import sandbox contract and synthetic live tests."""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

from app import import_sandbox
from app.main import parse_document_isolated


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
    if not shutil.which("bwrap"):
        pytest.skip("Bubblewrap is not available on this host")
    monkeypatch.setenv("GOREECLOUD_AI_IMPORT_ISOLATION", "bwrap")
    result = await parse_document_isolated("A synthetic résumé".encode(), "txt")
    assert result == {"text": "A synthetic résumé", "truncated": False}


def test_real_sandbox_denies_host_path_and_network(tmp_path, monkeypatch):
    if not shutil.which("bwrap"):
        pytest.skip("Bubblewrap is not available on this host")
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
