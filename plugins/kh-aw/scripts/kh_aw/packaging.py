from __future__ import annotations

import os
import zipfile
import json
from pathlib import Path
from typing import Any

from .integrity import iter_package_files
from .util import sha256_file


ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def build_deterministic_zip(plugin_root: Path, output_path: Path) -> dict[str, Any]:
    plugin_root = plugin_root.resolve()
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in iter_package_files(plugin_root):
            relative = path.relative_to(plugin_root).as_posix()
            info = zipfile.ZipInfo(f"kh-aw/{relative}", ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if os.access(path, os.X_OK) else 0o644) << 16
            archive.writestr(info, path.read_bytes())
        manifest = plugin_root / "PACKAGE_MANIFEST.json"
        info = zipfile.ZipInfo("kh-aw/PACKAGE_MANIFEST.json", ZIP_TIMESTAMP)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, manifest.read_bytes())
    return {
        "path": output_path.as_posix(),
        "sha256": sha256_file(output_path),
        "bytes": output_path.stat().st_size,
    }


def build_release_manifest(marketplace_root: Path) -> dict[str, Any]:
    root = marketplace_root.resolve()
    excluded_parts = {".git", "__pycache__", ".pytest_cache", "node_modules", "dist"}
    excluded_names = {"RELEASE_MANIFEST.json"}
    paths = [
        path for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.name not in excluded_names
        and not set(path.relative_to(root).parts) & excluded_parts
    ]
    files = [{
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    } for path in paths]
    plugin = json.loads(
        (root / "plugins" / "kh-aw" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    return {
        "schemaVersion": "4.0",
        "plugin": "kh-aw",
        "version": str(plugin.get("version", "")),
        "fileCount": len(files),
        "totalBytes": sum(item["bytes"] for item in files),
        "files": files,
    }
