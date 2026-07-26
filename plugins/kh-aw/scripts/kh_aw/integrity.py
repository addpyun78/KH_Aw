from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import sha256_bytes, sha256_file, utc_now, write_json, read_json

EXCLUDED_PARTS = {"node_modules", "__pycache__", ".pytest_cache", ".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log"}
MANIFEST_NAME = "PACKAGE_MANIFEST.json"
TEXT_SUFFIXES = {
    ".json", ".jsonl", ".md", ".txt", ".py", ".js", ".mjs", ".ts", ".tsx",
    ".yaml", ".yml", ".toml", ".xml", ".html", ".css", ".sh", ".ps1", ".bat",
}


def normalized_lf_bytes(path: Path) -> bytes | None:
    if path.suffix and path.suffix.lower() not in TEXT_SUFFIXES:
        return None
    try:
        raw = path.read_bytes()
        raw.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def package_file_record(path: Path, plugin_root: Path) -> dict[str, Any]:
    record = {
        "path": path.relative_to(plugin_root).as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }
    normalized = normalized_lf_bytes(path)
    if normalized is not None:
        record["normalizedLfSha256"] = sha256_bytes(normalized)
        record["normalizedLfBytes"] = len(normalized)
    return record


def iter_package_files(plugin_root: Path):
    for path in sorted(plugin_root.rglob("*")):
        if not path.is_file() or path.name == MANIFEST_NAME:
            continue
        rel = path.relative_to(plugin_root)
        if any(part in EXCLUDED_PARTS for part in rel.parts) or path.suffix.lower() in EXCLUDED_SUFFIXES:
            continue
        yield path


def build_package_manifest(plugin_root: Path) -> dict[str, Any]:
    plugin_root = plugin_root.resolve()
    files = [package_file_record(path, plugin_root) for path in iter_package_files(plugin_root)]
    plugin = read_json(plugin_root / ".codex-plugin" / "plugin.json", {})
    payload = {
        "schemaVersion": "4.0",
        "generatedAt": utc_now(),
        "plugin": "kh-aw",
        "version": str(plugin.get("version", "")),
        "lineEndingPolicy": "raw-or-normalized-lf-for-utf8-text",
        "fileCount": len(files),
        "files": files,
    }
    write_json(plugin_root / MANIFEST_NAME, payload)
    return payload


def validate_package_manifest(plugin_root: Path) -> list[str]:
    plugin_root = plugin_root.resolve()
    payload = read_json(plugin_root / MANIFEST_NAME, None)
    if not isinstance(payload, dict):
        return ["PACKAGE_MANIFEST.json is missing or invalid"]
    expected = {str(item.get("path")): item for item in payload.get("files", []) if isinstance(item, dict)}
    actual_paths = {path.relative_to(plugin_root).as_posix(): path for path in iter_package_files(plugin_root)}
    errors: list[str] = []
    missing = sorted(set(expected) - set(actual_paths))
    extra = sorted(set(actual_paths) - set(expected))
    if missing:
        errors.append(f"package manifest missing physical files: {missing}")
    if extra:
        errors.append(f"package manifest does not cover files: {extra}")
    for rel, path in actual_paths.items():
        item = expected.get(rel)
        if not item:
            continue
        raw_match = item.get("sha256") == sha256_file(path) and item.get("bytes") == path.stat().st_size
        normalized = normalized_lf_bytes(path)
        normalized_match = (
            normalized is not None
            and item.get("normalizedLfSha256", item.get("sha256")) == sha256_bytes(normalized)
            and item.get("normalizedLfBytes", item.get("bytes")) == len(normalized)
        )
        if not raw_match and not normalized_match:
            errors.append(f"package manifest hash/size mismatch: {rel}")
    if payload.get("fileCount") != len(expected):
        errors.append("package manifest fileCount mismatch")
    return errors
