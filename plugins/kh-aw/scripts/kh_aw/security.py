from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .util import iter_files, safe_relative, sha256_file, utc_now

FORBIDDEN_PATH_PARTS = {
    ".playwright-cli", "node_modules", ".gradle", "browser-profile", "user-data-dir",
    "cookies", "login data", "web data", "crashpad", "runtime-prompts", "scratch",
}
FORBIDDEN_FILE_NAMES = {
    ".env", ".env.local", ".env.production", "id_rsa", "id_ed25519", "credentials.json",
    "service-account.json", "cookies.sqlite", "login data", "web data",
}
SECRET_PATTERNS = [
    ("OPENAI_KEY", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("GITHUB_TOKEN", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("AWS_ACCESS_KEY", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("PRIVATE_KEY", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("GENERIC_SECRET_ASSIGNMENT", re.compile(r"(?i)\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|password)\s*[:=]\s*['\"][^'\"]{12,}['\"]")),
]
TEXT_SUFFIXES = {".txt", ".md", ".json", ".yaml", ".yml", ".toml", ".xml", ".html", ".css", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".py", ".kt", ".java", ".properties", ".env", ".sh", ".ps1", ".bat"}


def scan_release_root(root: Path) -> dict[str, Any]:
    root = root.resolve()
    findings: list[dict[str, Any]] = []
    file_count = 0
    total_bytes = 0
    for path in iter_files(root, include_ignored=True):
        file_count += 1
        try:
            size = path.stat().st_size
        except OSError:
            findings.append({"code": "UNREADABLE_FILE", "path": safe_relative(path, root), "severity": "major"})
            continue
        total_bytes += size
        rel = safe_relative(path, root)
        lowered_parts = {part.lower() for part in path.relative_to(root).parts}
        lower_name = path.name.lower()
        forbidden_hits = sorted(part for part in FORBIDDEN_PATH_PARTS if part in lowered_parts or part == lower_name)
        if forbidden_hits:
            findings.append({"code": "FORBIDDEN_RUNTIME_OR_PROFILE_PATH", "path": rel, "severity": "critical", "matches": forbidden_hits})
        if lower_name in FORBIDDEN_FILE_NAMES or lower_name.endswith((".db-wal", ".db-journal", ".sqlite", ".sqlite3")):
            findings.append({"code": "SENSITIVE_FILE_NAME", "path": rel, "severity": "critical"})
        if size <= 2 * 1024 * 1024 and (path.suffix.lower() in TEXT_SUFFIXES or lower_name.startswith(".env")):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for code, pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    findings.append({"code": code, "path": rel, "severity": "critical"})
    return {
        "schemaVersion": "3.0",
        "scannedAt": utc_now(),
        "scannedRoot": root.as_posix(),
        "rootExists": root.is_dir(),
        "fileCount": file_count,
        "totalBytes": total_bytes,
        "findings": findings,
        "status": "passed" if root.is_dir() and not findings else "failed",
    }
