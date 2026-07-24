from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import sha256_file, utc_now, write_json, read_json

EXCLUDED_PARTS = {"node_modules", "__pycache__", ".pytest_cache", ".DS_Store"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".log"}
MANIFEST_NAME = "PACKAGE_MANIFEST.json"


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
    files = [
        {
            "path": path.relative_to(plugin_root).as_posix(),
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in iter_package_files(plugin_root)
    ]
    payload = {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "plugin": "kh-aw",
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
        if item.get("sha256") != sha256_file(path) or item.get("bytes") != path.stat().st_size:
            errors.append(f"package manifest hash/size mismatch: {rel}")
    if payload.get("fileCount") != len(expected):
        errors.append("package manifest fileCount mismatch")
    return errors
