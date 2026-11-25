"""Source-level native Android animation preference contract.

No device, network, secrets, or production data are touched by this check.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "android/app/src/main/java/com/goreecloud/ai/MainActivity.kt"
THEME = ROOT / "android/gc-ui-compose/src/main/java/com/goreecloud/ui/material3/GoreeCloudExpressiveTheme.kt"


def test_ai_android_host_respects_disabled_system_animations():
    host = MAIN.read_text(encoding="utf-8")
    theme = THEME.read_text(encoding="utf-8")
    assert "import android.animation.ValueAnimator" in host
    assert "GoreeCloudExpressiveTheme(" in host
    assert "reduceMotion = !ValueAnimator.areAnimatorsEnabled()" in host
    assert "dynamicWallpaperColors = false" in host
    assert "accent = GoreeAccent.Iris" in host
    assert "AiWorkspace() }" in host
    assert "MotionScheme.standard() else MotionScheme.expressive()" in theme


def test_ai_android_host_retains_workspace_entrypoint():
    host = MAIN.read_text(encoding="utf-8")
    assert host.count("GoreeCloudExpressiveTheme(") == 1
    assert "@Composable\nprivate fun AiWorkspace()" in host
