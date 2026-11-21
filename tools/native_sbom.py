"""Limited native-component inventories, never a resolved Gradle/Qt SBOM.

Android data is ONLY first-party Gradle source declarations. Qt runtime data
is ONLY selected PySide6 Python wheels installed in the invoking environment.
No host paths, tokens, prompts, dependency edge or license claims.
"""
import re
from importlib import metadata
from pathlib import Path
from urllib.parse import quote

DEPENDENCY = re.compile(
    r'^\s*(?P<scope>implementation|api|testImplementation)\('
    r'"(?P<group>[a-zA-Z0-9_.-]+):(?P<artifact>[a-zA-Z0-9_.-]+):'
    r'(?P<version>[^"\s]+)"\)\s*$', re.MULTILINE,
)
PLUGIN = re.compile(
    r'^\s*id\("(?P<id>[a-zA-Z0-9_.-]+)"\) '
    r'version "(?P<version>[^"\s]+)" apply false\s*$', re.MULTILINE,
)
PINNED_VERSION = re.compile(r"\d+(?:[.][0-9A-Za-z_-]+)+")


def _purl(ecosystem: str, namespace: str, name: str, version: str) -> str:
    return "pkg:" + ecosystem + "/" + (
        quote(namespace, safe="") + "/" if namespace else ""
    ) + quote(name, safe="") + "@" + quote(version, safe="")


def _pinned(version: str) -> str:
    if not PINNED_VERSION.fullmatch(version):
        raise ValueError("Native dependency must declare a literal fixed version")
    return version


def android_declared_components(root: Path) -> list[dict]:
    """Declared Android dependencies/plugins, NOT Gradle-resolved transitive graph."""
    results: dict[str, dict] = {}
    for module in ("android/app/build.gradle.kts",
                   "android/gc-ui-compose/build.gradle.kts"):
        text = (root / module).read_text(encoding="utf-8")
        found = list(DEPENDENCY.finditer(text))
        # Fail closed if a Gradle dependency changes from literal Maven syntax
        # to a version catalog, dynamic expression or unknown syntax. Skipping
        # it would make this *direct declaration* inventory misleading.
        declarations = re.findall(
            r"^\s*(?:implementation|api|testImplementation)\(", text, re.MULTILINE
        )
        local_projects = re.findall(
            r"^\s*(?:implementation|api|testImplementation)\(project\(", text,
            re.MULTILINE,
        )
        if not found or len(found) + len(local_projects) != len(declarations):
            raise ValueError("Unsupported or unpinned Android dependency declaration")
        for match in found:
            group, artifact = match.group("group", "artifact")
            version = _pinned(match.group("version"))
            purl = _purl("maven", group, artifact, version)
            excluded = match.group("scope") == "testImplementation"
            if purl in results:
                existing = results[purl]
                # A package used in production must not be marked test-only.
                if not excluded:
                    existing.pop("scope", None)
                existing["properties"][0]["value"] = ";".join(sorted(set(
                    existing["properties"][0]["value"].split(";") + [module]
                )))
                continue
            item = {
                "type": "library", "group": group, "name": artifact,
                "version": version, "purl": purl, "bom-ref": purl,
                "properties": [{"name": "goreecloud:declared-in", "value": module}],
            }
            if excluded:
                item["scope"] = "excluded"
            results[purl] = item

    plugin_source = "android/build.gradle.kts"
    source = (root / plugin_source).read_text(encoding="utf-8")
    plugins = list(PLUGIN.finditer(source))
    declarations = re.findall(r'^\s*id\("', source, re.MULTILINE)
    if not plugins or len(plugins) != len(declarations):
        raise ValueError("Missing pinned Gradle plugin source declarations")
    for match in plugins:
        name, version = match.group("id"), _pinned(match.group("version"))
        # A Gradle plugin ID is NOT necessarily its actual resolved Maven artifact.
        # Use a generic source-declaration purl rather than fabricating coordinates.
        purl = _purl("generic", "gradle-plugin-id", name, version)
        results[purl] = {
            "type": "framework", "name": name, "version": version,
            "purl": purl, "bom-ref": purl,
            "properties": [
                {"name": "goreecloud:declared-in", "value": plugin_source},
                {"name": "goreecloud:resolution", "value": "plugin-id-only-not-gradle-artifact"},
            ],
        }
    return sorted(results.values(), key=lambda item: item["bom-ref"])


def qt_installed_components() -> list[dict]:
    """Enumerate selected installed PySide6 wheels, not OS/Qt native libraries."""
    labels = (
        "PySide6", "PySide6-Addons", "PySide6-Essentials",
        "PySide6-WebEngine", "PySide6-Pdf", "shiboken6",
    )
    result = []
    for name in labels:
        try:
            version = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
        version = _pinned(version)
        purl = _purl("pypi", "", name.lower().replace("_", "-"), version)
        result.append({
            "type": "library", "name": name, "version": version,
            "purl": purl, "bom-ref": purl,
            "properties": [{"name": "goreecloud:resolution",
                            "value": "installed-wheel-not-full-Qt-runtime"}],
        })
    if not any(item["name"] == "PySide6" for item in result):
        raise ValueError("Qt runtime wheel inventory requires installed PySide6")
    return sorted(result, key=lambda item: item["bom-ref"])
