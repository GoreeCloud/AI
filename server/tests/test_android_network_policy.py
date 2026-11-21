"""Static source-policy checks for strict release and narrow debug cleartext.

These tests do not certify the merged runtime manifest or physical devices.
"""
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ANDROID = "{http://schemas.android.com/apk/res/android}"
DEBUG_XML = "android/app/src/debug/res/xml/goree_ai_debug_network_security.xml"
DEBUG_MANIFEST = "android/app/src/debug/AndroidManifest.xml"
MAIN_MANIFEST = "android/app/src/main/AndroidManifest.xml"


def inspect_android_network_policy(root: Path):
    main = ET.parse(root / MAIN_MANIFEST).getroot()
    app = main.find("application")
    assert app is not None
    if app.get(ANDROID + "usesCleartextTraffic") != "false":
        raise ValueError("Release must not enable cleartext")
    if app.get(ANDROID + "allowBackup") != "false":
        raise ValueError("Release must prohibit app backup")
    if app.get(ANDROID + "networkSecurityConfig"):
        raise ValueError("Debug network policy must not be included in main")
    if (root / "android/app/src/release/res/xml/goree_ai_debug_network_security.xml").exists():
        raise ValueError("Debug network policy must not be in release resources")

    debug = ET.parse(root / DEBUG_MANIFEST).getroot().find("application")
    if debug is None or debug.get(ANDROID + "networkSecurityConfig") != (
        "@xml/goree_ai_debug_network_security"
    ):
        raise ValueError("Debug network policy missing")
    if debug.get(ANDROID + "usesCleartextTraffic"):
        raise ValueError("Debug must scope cleartext using XML, not manifest-wide")

    config = ET.parse(root / DEBUG_XML).getroot()
    if config.tag != "network-security-config":
        raise ValueError("Invalid network policy root")
    defaults = config.findall("base-config")
    if len(defaults) != 1 or defaults[0].get("cleartextTrafficPermitted") != "false":
        raise ValueError("Default network traffic must remain HTTPS")
    configs = config.findall("domain-config")
    if len(configs) != 1 or configs[0].get("cleartextTrafficPermitted") != "true":
        raise ValueError("Exactly one debug-only cleartext domain exception required")
    domains = configs[0].findall("domain")
    if len(domains) != 1 or (domains[0].text or "").strip() != "10.0.2.2":
        raise ValueError("Only Android emulator loopback alias is permitted")
    if domains[0].get("includeSubdomains") != "false":
        raise ValueError("Wildcard debug network exceptions forbidden")
    other = [child.tag for child in config if child.tag not in ("base-config", "domain-config")]
    if other or configs[0].find("trust-anchors") is not None:
        raise ValueError("Extra network security/trust anchors must be reviewed")

    # Actual Kotlin URL validation must independently reject non-HTTPS
    # except emulator loopback behind BuildConfig.DEBUG.
    kotlin = (root / "android/app/src/main/java/com/goreecloud/ai/AiApi.kt").read_text()
    if not all(value in kotlin for value in (
        "BuildConfig.DEBUG &&", 'target.host == "10.0.2.2"',
        'target.protocol == "https" || isEmulatorDevelopment',
        "connection.instanceFollowRedirects = false",
    )):
        raise ValueError("Native client HTTP policy differs from debug exception")


def test_source_policy_is_tightly_scoped():
    inspect_android_network_policy(ROOT)


def _copy_sources(tmp_path):
    paths = [
        MAIN_MANIFEST, DEBUG_MANIFEST, DEBUG_XML,
        "android/app/src/main/java/com/goreecloud/ai/AiApi.kt",
    ]
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return tmp_path


def test_reject_widened_debug_base(tmp_path):
    root = _copy_sources(tmp_path)
    xml = root / DEBUG_XML
    xml.write_text(xml.read_text().replace(
        '<base-config cleartextTrafficPermitted="false"',
        '<base-config cleartextTrafficPermitted="true"'))
    with pytest.raises(ValueError, match="Default"):
        inspect_android_network_policy(root)


@pytest.mark.parametrize("hostname", ["example.test", "10.0.2.3", "*.local"])
def test_reject_unexpected_http_host(tmp_path, hostname):
    root = _copy_sources(tmp_path)
    xml = root / DEBUG_XML
    xml.write_text(xml.read_text().replace(">10.0.2.2<", ">" + hostname + "<"))
    with pytest.raises(ValueError, match="Only Android emulator"):
        inspect_android_network_policy(root)


def test_reject_release_cleartext_and_debug_configuration_leak(tmp_path):
    root = _copy_sources(tmp_path)
    manifest = root / MAIN_MANIFEST
    manifest.write_text(manifest.read_text().replace(
        'android:usesCleartextTraffic="false"',
        'android:usesCleartextTraffic="true"'))
    with pytest.raises(ValueError, match="Release"):
        inspect_android_network_policy(root)
    manifest.write_text((ROOT / MAIN_MANIFEST).read_text().replace(
        'android:allowBackup="false"', 'android:allowBackup="true"'))
    with pytest.raises(ValueError, match="Release"):
        inspect_android_network_policy(root)


def test_reject_misaligned_native_transport(tmp_path):
    root = _copy_sources(tmp_path)
    kotlin = root / "android/app/src/main/java/com/goreecloud/ai/AiApi.kt"
    kotlin.write_text(kotlin.read_text().replace('BuildConfig.DEBUG &&', 'true &&'))
    with pytest.raises(ValueError, match="Native client HTTP"):
        inspect_android_network_policy(root)
