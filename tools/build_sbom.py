"""Deterministic CycloneDX 1.6 component inventories from committed lockfiles.

These catalogs are NOT vulnerability scans, license audits, signatures,
deployment attestations, or proof of resolved transitive dependency edges.
"""
import argparse
import json
import tomllib
from pathlib import Path
from urllib.parse import quote

from native_sbom import android_declared_components, qt_installed_components

ROOT = Path(__file__).resolve().parent.parent


def _component(name: str, version: str, ecosystem: str, *, excluded=False) -> dict:
    escaped = "/".join(quote(part, safe="") for part in name.split("/"))
    purl = f"pkg:{ecosystem}/{escaped}@{quote(version, safe='')}"
    value = {"type": "library", "name": name, "version": version, "purl": purl, "bom-ref": purl}
    if excluded:
        value["scope"] = "excluded"
    return value


def python_components(root: Path) -> list[dict]:
    parsed = tomllib.loads((root / "server/uv.lock").read_text(encoding="utf-8"))
    entries = parsed.get("package")
    if not isinstance(entries, list):
        raise ValueError("Invalid uv.lock package inventory")
    results: dict[str, dict] = {}
    for package in entries:
        if not isinstance(package, dict):
            raise ValueError("Unexpected uv.lock package")
        source = package.get("source")
        name = package.get("name")
        version = package.get("version")
        if isinstance(source, dict) and source.get("editable"):
            continue
        if (not isinstance(name, str) or not isinstance(version, str)
                or not isinstance(source, dict)):
            if isinstance(source, dict) and source.get("editable"):
                continue
            raise ValueError("Invalid uv.lock name/version/source")
        if source.get("registry") != "https://pypi.org/simple":
            raise ValueError("Unapproved Python third-party registry requires review")
        item = _component(name.lower(), version, "pypi")
        results[item["bom-ref"]] = item
    if not results:
        raise ValueError("No pinned Python packages")
    return sorted(results.values(), key=lambda x: x["bom-ref"])


def npm_components(root: Path) -> list[dict]:
    parsed = json.loads((root / "web/package-lock.json").read_text(encoding="utf-8"))
    entries = parsed.get("packages")
    if parsed.get("lockfileVersion") != 3 or not isinstance(entries, dict):
        raise ValueError("Unsupported npm lockfile")
    results: dict[str, dict] = {}
    for location, details in entries.items():
        if location == "":
            continue
        if not location.startswith("node_modules/") or not isinstance(details, dict):
            raise ValueError("Unsupported npm package layout")
        name = location.rsplit("node_modules/", 1)[-1]
        version = details.get("version")
        if not isinstance(version, str) or not version or not name:
            raise ValueError("Unpinned npm package")
        item = _component(name, version, "npm", excluded=details.get("dev") is True)
        previous = results.get(item["bom-ref"])
        if previous and previous.get("scope") != "excluded":
            continue
        results[item["bom-ref"]] = item
    if not results:
        raise ValueError("No pinned npm packages")
    return sorted(results.values(), key=lambda x: x["bom-ref"])


def _bom(name: str, components: list[dict], coverage: str) -> dict:
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "metadata": {
            "component": {"type": "application", "name": name, "version": "0.1.0"},
            "properties": [{"name": "goreecloud:inventory-coverage", "value": coverage}],
        },
        "components": components,
    }


def build(output: Path, root: Path = ROOT, *, include_qt_runtime: bool = False) -> tuple[Path, ...]:
    output.mkdir(mode=0o700, parents=True, exist_ok=True)
    paths = []
    inventories = [
        ("python.cdx.json", "goreecloud-ai-server", python_components(root),
         "committed-uv-lock-packages-not-full-dependency-graph"),
        ("web.cdx.json", "goreecloud-ai-web", npm_components(root),
         "committed-npm-lock-packages-not-full-dependency-graph"),
        ("android-direct.cdx.json", "goreecloud-ai-android", android_declared_components(root),
         "source-declared-direct-maven-and-plugin-ids-only"),
    ]
    if include_qt_runtime:
        inventories.append((
            "qt-runtime.cdx.json", "goreecloud-ai-linux-qt",
            qt_installed_components(), "selected-installed-pyside6-wheel-versions-only",
        ))
    for filename, name, components, coverage in inventories:
        path = output / filename
        path.write_text(json.dumps(_bom(name, components, coverage), indent=2, sort_keys=True)
                        + "\n", encoding="utf-8")
        paths.append(path)
    return tuple(paths)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("dist/sbom"))
    parser.add_argument("--include-qt-runtime", action="store_true",
                        help="Add selected installed Qt Python wheel versions (not OS/Qt libraries)")
    args = parser.parse_args()
    for path in build(args.output, include_qt_runtime=args.include_qt_runtime):
        print(f"Created {path}")


if __name__ == "__main__":
    main()
