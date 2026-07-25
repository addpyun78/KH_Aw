from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .util import slug, utc_now, write_json

PAGE_FILE_SUFFIXES = {
    ".cs", ".dart", ".html", ".htm", ".java", ".js", ".jsx", ".kt", ".php",
    ".py", ".svelte", ".swift", ".ts", ".tsx", ".vue",
}
ROUTE_PATTERNS = (
    re.compile(r"""(?:path|route|href|to)\s*[:=]\s*["']([^"'#?]+)["']""", re.I),
    re.compile(r"""(?:navigate|push|replace)\(\s*["']([^"'#?]+)["']""", re.I),
    re.compile(r"""@(?:app|router|blueprint)\.(?:get|post|put|delete|patch|route)\(\s*["']([^"'#?]+)["']""", re.I),
)


def _candidate_id(kind: str, evidence: str, entry: str) -> str:
    return f"PAGE-CANDIDATE-{slug(kind)}-{sha256_file_text(f'{evidence}|{entry}')[:12]}"


def sha256_file_text(value: str) -> str:
    import hashlib
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _add(
    candidates: dict[str, dict[str, Any]],
    *,
    kind: str,
    evidence: str,
    entry: str,
    reason: str,
) -> None:
    candidate_id = _candidate_id(kind, evidence, entry)
    candidates[candidate_id] = {
        "candidateId": candidate_id,
        "kind": kind,
        "sourceEvidence": evidence,
        "routeOrEntry": entry,
        "requiredBecause": reason,
    }


def build_page_candidates(source_root: Path, out_path: Path) -> dict[str, Any]:
    root = source_root.resolve()
    candidates: dict[str, dict[str, Any]] = {}
    scanned_files = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        parts = {part.lower() for part in path.parts}
        if parts.intersection({".git", ".kh_aw", "node_modules", "build", "dist", ".gradle"}):
            continue
        scanned_files += 1
        suffix = path.suffix.lower()
        lower_name = path.stem.lower()
        if suffix in {".html", ".htm"}:
            _add(
                candidates,
                kind="html-page",
                evidence=relative,
                entry=relative,
                reason="A physical HTML document can be a user-visible page or WebView entry.",
            )
        if suffix in {".kt", ".java"} and any(token in lower_name for token in ("activity", "fragment", "screen")):
            _add(
                candidates,
                kind="android-screen",
                evidence=relative,
                entry=path.stem,
                reason="An Android Activity or Fragment is a source screen candidate.",
            )
        if suffix == ".xml" and "layout" in parts:
            _add(
                candidates,
                kind="android-layout",
                evidence=relative,
                entry=path.stem,
                reason="An Android layout can represent a user-visible screen or dialog.",
            )
        if suffix == ".swift" and (
            lower_name.endswith("view")
            or lower_name.endswith("viewcontroller")
            or "viewcontroller" in lower_name
        ):
            _add(
                candidates,
                kind="ios-screen",
                evidence=relative,
                entry=path.stem,
                reason="A SwiftUI View or ViewController is a source screen candidate.",
            )
        normalized = relative.lower()
        if suffix in {".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"} and (
            "/pages/" in f"/{normalized}"
            or "/routes/" in f"/{normalized}"
            or normalized.endswith(("/page.js", "/page.jsx", "/page.ts", "/page.tsx"))
        ):
            _add(
                candidates,
                kind="framework-page",
                evidence=relative,
                entry=relative,
                reason="A framework page or route module is a user-visible page candidate.",
            )
        if suffix == ".dart" and any(token in lower_name for token in ("screen", "page", "view")):
            _add(
                candidates,
                kind="flutter-screen",
                evidence=relative,
                entry=path.stem,
                reason="A Flutter screen, page, or view source file is a user-visible page candidate.",
            )
        if suffix in {".php", ".cs"} and any(token in lower_name for token in ("page", "view", "controller")):
            _add(
                candidates,
                kind="server-rendered-page",
                evidence=relative,
                entry=relative,
                reason="A server-rendered page, view, or controller can expose a user-visible route.",
            )
        if suffix not in PAGE_FILE_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if suffix == ".kt" and "@Composable" in text and re.search(r"\b\w*(?:Screen|Page|View)\s*\(", text):
            _add(
                candidates,
                kind="android-compose-screen",
                evidence=relative,
                entry=path.stem,
                reason="A Jetpack Compose screen function is a user-visible page candidate.",
            )
        if suffix == ".swift" and re.search(r"\bstruct\s+\w+\s*:\s*View\b", text):
            _add(
                candidates,
                kind="swiftui-screen",
                evidence=relative,
                entry=path.stem,
                reason="A SwiftUI View declaration is a user-visible page candidate.",
            )
        for pattern in ROUTE_PATTERNS:
            for route in pattern.findall(text):
                route = route.strip()
                if not route or route.startswith(("http://", "https://", "javascript:")):
                    continue
                _add(
                    candidates,
                    kind="declared-route",
                    evidence=relative,
                    entry=route,
                    reason="A route, navigation target, or link was declared in source code.",
                )
    payload = {
        "schemaVersion": "3.2",
        "generatedAt": utc_now(),
        "sourceRoot": root.as_posix(),
        "scannedFileCount": scanned_files,
        "candidateCount": len(candidates),
        "candidates": sorted(candidates.values(), key=lambda item: item["candidateId"]),
    }
    write_json(out_path, payload)
    return payload
