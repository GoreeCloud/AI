"""Offline, bounded first-party Compose Multiplatform provenance/host contract checks.

No external calls or credentials. Source checks are not Kotlin compilation,
Android runtime acceptance, iOS packaging or resolved third-party SBOM.
"""
import hashlib
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "android/vendor/gc-ui"
MANIFEST = VENDOR / "SOURCE-MANIFEST.json"
PIN = "f501d92ba1f6698fa99427c564bf838954ce8bc1"


def text(path):
    return (ROOT / path).read_text(encoding="utf-8")


class ComposeSourceIntegration(unittest.TestCase):
    def test_exact_pinned_source_manifest(self):
        d = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(d["schemaVersion"], 1)
        self.assertEqual(d["sourceRepo"], "GoreeCloud/gc-ui")
        self.assertEqual(d["sourceCommit"], PIN)
        observed = {}
        for location in [VENDOR / "LICENSE", VENDOR / "gc.tokens.json",
                         *(VENDOR / "compose-multiplatform").rglob("*"),
                         *(ROOT / "android/gc-ui-compose").rglob("*")]:
            if not location.is_file() or location.name in {"UPSTREAM.md", "SOURCE-MANIFEST.json"}:
                continue
            self.assertFalse(location.is_symlink(), location)
            observed[location.relative_to(ROOT).as_posix()] = hashlib.sha256(location.read_bytes()).hexdigest()
        self.assertEqual(d["sourceFilesSha256"], observed)
        self.assertEqual(
            (ROOT / "design/gc.tokens.json").read_bytes(),
            (VENDOR / "gc.tokens.json").read_bytes()
        )

    def test_android_and_shared_palettes_are_identical(self):
        android = text("android/gc-ui-compose/src/main/java/com/goreecloud/ui/material3/GeneratedGoreePalettes.kt")
        shared = text("android/vendor/gc-ui/compose-multiplatform/gc-ui-compose/src/commonMain/kotlin/com/goreecloud/ui/multiplatform/GeneratedGoreePalettes.kt")
        self.assertEqual(
            android.replace("package com.goreecloud.ui.material3", "package SHARED"),
            shared.replace("package com.goreecloud.ui.multiplatform", "package SHARED")
        )
        for accent in ("iris", "lagoon", "ember", "moss"):
            for mode in ("light", "dark"):
                self.assertIn(f'"{accent}/{mode}"', shared)

    def test_shared_ui_reuses_android_expressive_outer_theme(self):
        root_gradle = text("android/build.gradle.kts")
        settings = text("android/settings.gradle.kts")
        app_gradle = text("android/app/build.gradle.kts")
        source = text("android/app/src/main/java/com/goreecloud/ai/MainActivity.kt")
        self.assertIn('id("org.jetbrains.kotlin.multiplatform") version "2.4.21"', root_gradle)
        self.assertIn('id("org.jetbrains.kotlin.plugin.compose") version "2.4.21"', root_gradle)
        self.assertIn('id("com.android.kotlin.multiplatform.library") version "9.2.0"', root_gradle)
        self.assertIn('include(":app", ":gc-ui-compose", ":gc-ui-shared")', settings)
        self.assertIn('project(":gc-ui-shared").projectDir', settings)
        self.assertIn('implementation(project(":gc-ui-shared"))', app_gradle)
        self.assertIn('implementation(project(":gc-ui-compose"))', app_gradle)
        self.assertIn('GoreeCloudExpressiveTheme(', source)
        self.assertIn('dynamicWallpaperColors = false', source)
        self.assertIn('reduceMotion = !ValueAnimator.areAnimatorsEnabled()', source)
        self.assertIn('GoreeCloudAction(label = "Cancel", onClick = { pendingDeleteId = "" })', source)
        self.assertNotIn('GoreeCloudMultiplatformTheme(', source)
        self.assertIn('cloudConsent = false', source)
        self.assertIn('reuseLocalResponse = false', source)
        self.assertIn('providerResponseCache = false', source)


if __name__ == "__main__":
    unittest.main()
