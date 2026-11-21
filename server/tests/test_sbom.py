"""No-provider, no-network tests for deterministic inventories from committed locks."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools/build_sbom.py"


def test_bom_generated_from_both_locks(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(tmp_path)],
        check=True, capture_output=True, text=True, cwd=ROOT,
    )
    assert "Created" in proc.stdout
    for name, expected in (("python.cdx.json", "pkg:pypi/"),
                           ("web.cdx.json", "pkg:npm/")):
        raw = (tmp_path / name).read_bytes()
        result = json.loads(raw)
        assert result["bomFormat"] == "CycloneDX"
        assert result["specVersion"] == "1.6"
        components = result["components"]
        assert len(components) >= 5
        assert all(c["purl"].startswith(expected) for c in components)
        assert all(c["version"] and c["name"] and c["bom-ref"] == c["purl"] for c in components)
        assert len({c["bom-ref"] for c in components}) == len(components)
        assert b"OPENROUTER_API_KEY" not in raw
        assert b"GOREECLOUD_AI_TOKEN" not in raw
        assert b"private" not in raw.lower()


def test_bom_repeatable_and_includes_pinned_crypto(tmp_path):
    subprocess.run([sys.executable, str(SCRIPT), "--output", str(tmp_path)],
                   check=True, stdout=subprocess.DEVNULL, cwd=ROOT)
    first = {p.name: p.read_bytes() for p in tmp_path.glob("*.cdx.json")}
    subprocess.run([sys.executable, str(SCRIPT), "--output", str(tmp_path)],
                   check=True, stdout=subprocess.DEVNULL, cwd=ROOT)
    assert first == {p.name: p.read_bytes() for p in tmp_path.glob("*.cdx.json")}
    python_bom = json.loads(first["python.cdx.json"])
    assert any(c["name"] == "cryptography" and c["version"] == "50.0.2"
               for c in python_bom["components"])
