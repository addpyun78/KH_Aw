from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .util import read_json

HANGUL_RE = re.compile(r"[\uac00-\ud7a3]")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
BROKEN_TEXT_MARKERS = ("\ufffd", "\u00ec", "\u00eb", "\u00ea")

INTERNAL_LEDGER_GLOBS = (
    "state.json",
    "analysis/**/*.json",
    "audit/**/*.json",
    "checkpoints/**/*.json",
    "contract/*.json",
    "design/**/*.json",
    "evidence/research-plan.json",
    "implementation/**/*.json",
    "orchestration/**/*.json",
    "release/**/*.json",
    "repairs/**/*.json",
    "reports/gate-*.json",
    "review/**/*.json",
    "test/**/*.json",
)

INTERNAL_LEDGER_EXCLUSIONS = {
    "contract/requirements.json",
    "contract/instruction-ledger.json",
    "contract/source-inventory.json",
    "evidence/source-registry.json",
}

USER_TEXT_KEYS = {
    "sourceText",
    "requirement",
    "originalInstruction",
    "userFacingText",
    "koreanUiText",
    "bodyExcerpt",
    "excerpt",
    "query",
    "title",
}

SOURCE_OR_PATH_KEYS = {
    "analysisFolder",
    "analysisSourceRoot",
    "archive",
    "bodyPath",
    "evidencePath",
    "file",
    "filePath",
    "implementationRoot",
    "instructionsFile",
    "logPath",
    "path",
    "projectRoot",
    "routeOrEntry",
    "runRoot",
    "source",
    "sourcePath",
    "sourceSessionPath",
    "targetFile",
    "url",
    "workspaceRoot",
}
MACHINE_OUTPUT_KEYS = {
    "error",
    "stdout",
    "stderr",
    "output",
    "versionOutput",
}


def language_policy() -> dict[str, Any]:
    return {
        "schemaVersion": "3.2",
        "internalLanguage": "en",
        "userFacingLanguage": "ko-KR",
        "internalArtifactsMustBeEnglish": True,
        "userInterfaceMustContainKorean": True,
        "brokenEncodingForbidden": True,
        "allowedInternalUserTextKeys": sorted(USER_TEXT_KEYS),
    }


def _walk_strings(value: Any, path: str = "$"):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _walk_strings(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_strings(child, f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def _field_is_language_exempt(field_path: str) -> bool:
    segments = re.findall(r"\.([A-Za-z][A-Za-z0-9_]*)", field_path)
    if not segments:
        return False
    leaf = segments[-1]
    if leaf in USER_TEXT_KEYS or leaf in SOURCE_OR_PATH_KEYS or leaf in MACHINE_OUTPUT_KEYS:
        return True
    return leaf.endswith(("Path", "Paths", "Root", "Url", "URL", "Uri", "URI", "Sha256"))


def internal_language_issues(run_root: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    paths: set[Path] = set()
    for pattern in INTERNAL_LEDGER_GLOBS:
        paths.update(path for path in run_root.glob(pattern) if path.is_file())
    for path in sorted(paths):
        relative = path.relative_to(run_root).as_posix()
        if relative in INTERNAL_LEDGER_EXCLUSIONS:
            continue
        payload = read_json(path, None)
        if payload is None:
            continue
        for field_path, text in _walk_strings(payload):
            if any(marker in text for marker in BROKEN_TEXT_MARKERS):
                issues.append({
                    "code": "BROKEN_INTERNAL_TEXT_DETECTED",
                    "message": "Codex-facing internal evidence contains broken encoding.",
                    "evidence": {"file": relative, "field": field_path},
                })
            if _field_is_language_exempt(field_path):
                continue
            if HANGUL_RE.search(text) or CJK_RE.search(text):
                issues.append({
                    "code": "INTERNAL_ARTIFACT_NOT_ENGLISH",
                    "message": "Codex-facing internal evidence must be written in English.",
                    "evidence": {"file": relative, "field": field_path},
                })
    return issues


def korean_ui_character_count(paths: list[Path]) -> int:
    count = 0
    for path in paths:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        count += len(HANGUL_RE.findall(text))
    return count
