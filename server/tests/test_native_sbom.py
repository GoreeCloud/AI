"""No-network native source-declaration inventory and selected-wheel tests.

Intentionally not a resolved Gradle or complete native-Qt dependency graph.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools/build_sbom.py"
NATIVE = ROOT / "tools/native_sbom.py"
spec = importlib.util.spec_from_file_location("native_sbom_for_tests", NATIVE)
assert spec and spec.loader
native_sbom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native_sbom)


def test_android_direct_inventory_is_exact_source_declared_and_bounded(tmp_path):
    subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(tmp_path)],
        check=True, cwd=ROOT, capture_output=True,
    )
    inventory = json.loads((tmp_path / "android-direct.cdx.json").read_text())
    assert inventory["specVersion"] == "1.6"
    assert inventory["metadata"]["properties"] == [
        {"name": "goreecloud:inventory-coverage",
         "value": "app-and-expressive-declarations-only-kmp-aliases-excluded"},
    ]
    components = inventory["components"]
    assert len(components) == 12
    assert all(c["bom-ref"] == c["purl"] for c in components)
    assert len({c["bom-ref"] for c in components}) == 12
    entries = {c["purl"]: c for c in components}
    assert entries["pkg:maven/androidx.compose.ui/ui@1.13.0"]["properties"] == [{
        "name": "goreecloud:declared-in",
        "value": "android/app/build.gradle.kts;android/gc-ui-compose/build.gradle.kts",
    }]
    assert entries["pkg:maven/junit/junit@4.13.2"]["scope"] == "excluded"
    assert entries["pkg:maven/androidx.activity/activity-compose@1.13.0"]["version"] == "1.13.0"
    assert entries[
        "pkg:generic/gradle-plugin-id/com.android.application@9.2.0"
    ]["properties"][1]["value"] == "plugin-id-only-not-gradle-artifact"
    assert entries[
        "pkg:generic/gradle-plugin-id/org.jetbrains.kotlin.multiplatform@2.4.21"
    ]["version"] == "2.4.21"
    assert entries[
        "pkg:generic/gradle-plugin-id/com.android.kotlin.multiplatform.library@9.2.0"
    ]["properties"][1]["value"] == "plugin-id-only-not-gradle-artifact"
    # Only app/Android host declarations are enumerated; commonMain's
    # plugin-managed Compose aliases do not pretend to be resolved Maven pins.
    assert "pkg:maven/com.goreecloud.ui/shared-compose@0.0.0" not in entries
    assert all("localhost" not in json.dumps(c) and "/home/" not in json.dumps(c)
               for c in components)


@pytest.mark.parametrize("bad", [
    'implementation("example.lib:unlocked:$version")',
    'implementation("example.lib:unlocked:1.+")',
    'implementation("example.lib:unlocked:[1.0,2.0)")',
    'implementation(libs.example.unpinned)',
])
def test_unpinned_native_versions_fail_instead_of_being_skipped(tmp_path, bad):
    (tmp_path / "android/app").mkdir(parents=True)
    (tmp_path / "android/gc-ui-compose").mkdir(parents=True)
    (tmp_path / "android/app/build.gradle.kts").write_text(
        'implementation("com.example:one:1.2.3")\\n' + bad + "\\n"
    )
    (tmp_path / "android/gc-ui-compose/build.gradle.kts").write_text(
        'implementation("com.example:two:4.5.6")\\n'
    )
    (tmp_path / "android/build.gradle.kts").write_text(
        'id("com.android.application") version "9.2.0" apply false\\n'
    )
    with pytest.raises(ValueError, match="Unsupported or unpinned"):
        native_sbom.android_declared_components(tmp_path)


def test_native_inventory_fails_closed_on_missing_plugin_pins(tmp_path):
    (tmp_path / "android/app").mkdir(parents=True)
    (tmp_path / "android/gc-ui-compose").mkdir(parents=True)
    (tmp_path / "android/app/build.gradle.kts").write_text(
        'implementation("com.example:one:1.2.3")\n')
    (tmp_path / "android/gc-ui-compose/build.gradle.kts").write_text(
        'implementation("com.example:two:4.5.6")\n')
    (tmp_path / "android/build.gradle.kts").write_text('plugins { id("com.android.application") }')
    with pytest.raises(ValueError, match="Missing pinned Gradle plugin"):
        native_sbom.android_declared_components(tmp_path)


def test_qt_inventory_reflects_selected_installed_wheels_only(monkeypatch):
    existing = {
        "PySide6": "6.12.1", "PySide6-Addons": "6.12.1",
        "PySide6-Essentials": "6.12.1", "shiboken6": "6.12.1",
    }

    def version(name):
        if name not in existing:
            raise native_sbom.metadata.PackageNotFoundError(name)
        return existing[name]

    monkeypatch.setattr(native_sbom.metadata, "version", version)
    components = native_sbom.qt_installed_components()
    assert len(components) == 4
    assert all(c["version"] == "6.12.1" for c in components)
    assert all(c["purl"].startswith("pkg:pypi/") for c in components)
    assert all(c["properties"][0]["value"] == "installed-wheel-not-full-Qt-runtime"
               for c in components)

    monkeypatch.setattr(
        native_sbom.metadata, "version",
        lambda name: (_ for _ in ()).throw(native_sbom.metadata.PackageNotFoundError(name)),
    )
    with pytest.raises(ValueError, match="installed PySide6"):
        native_sbom.qt_installed_components()


def test_inventory_output_has_no_raw_version_constraints_or_credentials(tmp_path):
    subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(tmp_path)],
        check=True, cwd=ROOT, capture_output=True,
    )
    for path in tmp_path.glob("*.cdx.json"):
        content = path.read_text()
        assert "OPENROUTER_API_KEY" not in content
        assert "GOREECLOUD_AI_TOKEN" not in content
        assert "GOREECLOUD_AI_DB_KEY" not in content
        assert "https://private" not in content
        assert "GOREECLOUD_AI_OIDC" not in content
