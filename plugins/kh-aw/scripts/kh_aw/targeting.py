from __future__ import annotations

import re
from pathlib import Path
from typing import Any

TARGET_PIPELINES = {
    "web-responsive",
    "app-mobile-webview",
    "android-native",
    "ios-native",
    "cross-platform",
    "unknown-needs-confirmation",
}

WEB_HINTS = (
    "webpage", "website", "web page", "responsive web", "landing page",
    "dashboard", "admin web",
)
WEBVIEW_HINTS = (
    "webview", "html mobile app", "html-based mobile app",
    "html based mobile app", "android webview",
)
ANDROID_HINTS = ("android app", "android native", "kotlin", "gradle")
IOS_HINTS = ("ios app", "swiftui", "xcode")

# Korean user instructions are input data. Unicode escapes keep the internal source ASCII.
KOREAN_WEB_HINTS = (
    "\uc6f9\ud398\uc774\uc9c0", "\uc6f9 \ud398\uc774\uc9c0", "\ubc18\uc751\ud615 \uc6f9",
    "\ub79c\ub529\ud398\uc774\uc9c0", "\uad00\ub9ac\uc790 \uc6f9", "\ub300\uc2dc\ubcf4\ub4dc",
)
KOREAN_WEBVIEW_HINTS = (
    "html\uae30\ubc18 \ubaa8\ubc14\uc77c\uc571", "html \uae30\ubc18 \ubaa8\ubc14\uc77c\uc571",
    "\uc548\ub4dc\ub85c\uc774\ub4dc webview", "\uc6f9\ubdf0",
)
KOREAN_ANDROID_HINTS = ("\uc548\ub4dc\ub85c\uc774\ub4dc \uc571", "\ub124\uc774\ud2f0\ube0c \uc571")


def infer_target_pipeline(instructions: str, project_root: Path | None = None) -> dict[str, Any]:
    text = instructions.lower()
    compact = re.sub(r"\s+", "", text)
    signals: list[str] = []

    webview = (
        any(hint in text for hint in WEBVIEW_HINTS)
        or any(hint.replace(" ", "") in compact for hint in KOREAN_WEBVIEW_HINTS)
    )
    web = (
        any(hint in text for hint in WEB_HINTS)
        or any(hint.replace(" ", "") in compact for hint in KOREAN_WEB_HINTS)
    )
    android = (
        any(hint in text for hint in ANDROID_HINTS)
        or any(hint.replace(" ", "") in compact for hint in KOREAN_ANDROID_HINTS)
    )
    ios = any(hint in text for hint in IOS_HINTS) or "ios" in text

    if project_root:
        root = project_root.resolve()
        package_json = root / "package.json"
        web_config = any((root / name).is_file() for name in (
            "vite.config.js", "vite.config.ts", "next.config.js", "next.config.mjs",
            "astro.config.mjs", "svelte.config.js", "nuxt.config.ts",
        ))
        web_assets = (
            any(root.glob("*.html"))
            or any(root.rglob("*.html"))
            or any(root.rglob("*.css"))
        )
        if package_json.is_file() or web_config or web_assets:
            web = True
            signals.append("web entrypoint, assets, or framework configuration detected")
        if (
            (root / "build.gradle").is_file()
            or (root / "build.gradle.kts").is_file()
            or any(root.rglob("AndroidManifest.xml"))
        ):
            android = True
            signals.append("Android project files detected")
        if any(root.rglob("*.xcodeproj")) or any(root.rglob("*.xcworkspace")):
            ios = True
            signals.append("iOS project files detected")

    if webview:
        signals.append("HTML mobile app or Android WebView instruction detected")
        return {"targetPipeline": "app-mobile-webview", "confidence": "high", "signals": signals}
    if android and web:
        signals.append("both app and web signals detected")
        return {"targetPipeline": "cross-platform", "confidence": "medium", "signals": signals}
    if android:
        signals.append("Android instruction or project detected")
        return {"targetPipeline": "android-native", "confidence": "medium", "signals": signals}
    if ios:
        signals.append("iOS instruction or project detected")
        return {"targetPipeline": "ios-native", "confidence": "medium", "signals": signals}
    if web:
        signals.append("web instruction or project detected")
        return {"targetPipeline": "web-responsive", "confidence": "medium", "signals": signals}
    return {
        "targetPipeline": "unknown-needs-confirmation",
        "confidence": "low",
        "signals": signals,
    }
