from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Any

from .util import iter_files, read_json, safe_relative, sha256_file, utc_now, write_json


def create_protected_snapshot(source: Path, run_root: Path) -> dict[str, Any]:
    source = source.resolve()
    if not source.is_dir():
        raise FileNotFoundError(source)
    protection = run_root / "protection"
    protection.mkdir(parents=True, exist_ok=True)
    archive = protection / "analysis-folder-backup.zip"
    manifest_entries: list[dict[str, Any]] = []
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in iter_files(source, include_ignored=True):
            rel = safe_relative(path, source)
            zf.write(path, rel)
            manifest_entries.append({"path": rel, "sizeBytes": path.stat().st_size, "sha256": sha256_file(path)})
    manifest = {
        "schemaVersion": "3.0",
        "createdAt": utc_now(),
        "source": source.as_posix(),
        "archive": archive.as_posix(),
        "archiveSha256": sha256_file(archive),
        "fileCount": len(manifest_entries),
        "files": manifest_entries,
    }
    write_json(protection / "analysis-snapshot.json", manifest)
    return manifest


def compare_snapshot(run_root: Path) -> dict[str, Any]:
    manifest = read_json(run_root / "protection" / "analysis-snapshot.json", {})
    source = Path(str(manifest.get("source", "")))
    expected = {item["path"]: item for item in manifest.get("files", []) if isinstance(item, dict) and item.get("path")}
    current: dict[str, dict[str, Any]] = {}
    if source.is_dir():
        for path in iter_files(source, include_ignored=True):
            rel = safe_relative(path, source)
            try:
                current[rel] = {"sizeBytes": path.stat().st_size, "sha256": sha256_file(path)}
            except OSError:
                current[rel] = {"sizeBytes": None, "sha256": "UNREADABLE"}
    missing = sorted(set(expected) - set(current))
    added = sorted(set(current) - set(expected))
    changed = sorted(path for path in set(expected) & set(current) if expected[path]["sha256"] != current[path]["sha256"])
    return {
        "ok": bool(source.is_dir()) and not (missing or added or changed),
        "sourceExists": source.is_dir(),
        "expectedCount": len(expected),
        "currentCount": len(current),
        "missing": missing,
        "added": added,
        "changed": changed,
    }


def restore_snapshot(run_root: Path) -> dict[str, Any]:
    manifest = read_json(run_root / "protection" / "analysis-snapshot.json", {})
    source = Path(str(manifest.get("source", "")))
    archive = Path(str(manifest.get("archive", "")))
    if not str(source) or not archive.is_file():
        return {"ok": False, "reason": "snapshot_missing"}
    if manifest.get("archiveSha256") and sha256_file(archive) != manifest.get("archiveSha256"):
        return {"ok": False, "reason": "snapshot_archive_hash_mismatch"}
    source.mkdir(parents=True, exist_ok=True)
    expected = {item["path"] for item in manifest.get("files", []) if isinstance(item, dict) and item.get("path")}
    for path in list(iter_files(source, include_ignored=True)):
        rel = safe_relative(path, source)
        if rel not in expected:
            path.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "r") as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            target = (source / member.filename).resolve()
            try:
                target.relative_to(source.resolve())
            except ValueError:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)
    check = compare_snapshot(run_root)
    return {"ok": check["ok"], "verification": check}
