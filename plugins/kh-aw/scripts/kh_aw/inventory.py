from __future__ import annotations

import csv
import json
import mimetypes
from pathlib import Path
from typing import Any

from .util import iter_files, line_count, safe_relative, sha256_file, utc_now, write_json

SENSITIVE_NAMES = {
    "cookies", "login data", "web data", "history", "credentials", "secrets",
    ".env", "id_rsa", "id_ed25519", "token", "account", "accounts", "apikey",
}


def classify(path: Path, root: Path) -> tuple[str, str, str]:
    rel = path.relative_to(root).as_posix()
    parts = {part.lower() for part in path.relative_to(root).parts}
    lower_name = path.name.lower()
    if ".git" in parts:
        return "vcs", "exclude", "Git internals are inventoried but are not product or plugin runtime content."
    if "node_modules" in parts or ".gradle" in parts:
        return "dependency-cache", "exclude", "Dependencies must be restored from lockfiles, not published as source."
    if ".playwright-cli" in parts or ("browser" in parts and path.suffix.lower() in {".db", ".pma", ".bdic"}):
        return "browser-profile", "exclude-sensitive", "Browser profiles may contain cookies, sessions, or machine-specific cache."
    if any(token in lower_name for token in SENSITIVE_NAMES) or path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".db-wal", ".db-journal"}:
        return "potential-sensitive-data", "exclude-sensitive", "Potential account, cookie, session, database, or secret material."
    if any(part in parts for part in {"output", "scratch", ".logs", "logs", "data"}):
        return "runtime-generated", "exclude", "Generated runs, logs, and user data are not distributable plugin source."
    if ".bak" in lower_name or ".corrupt-" in lower_name or ".last-good" in lower_name:
        return "backup", "exclude", "Backup/corrupt copies are inventoried but not shipped in runtime."
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
        return "image", "review", "Image requires branding, rights, and usage review."
    if rel.startswith(("backend/", "shared/", "config/", "tests/", "frontend/", ".agents/", "app/", "src/")):
        return "core-source", "mapped-or-replaced", "Core behavior must be mapped into implementation and evidence ledgers."
    return "project-file", "review", "Accounted for in the complete inventory."


def build_inventory(root: Path, out_dir: Path, *, include_all: bool = True, excluded_roots: tuple[Path, ...] = ()) -> dict[str, Any]:
    root = root.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, Any]] = []
    totals: dict[str, int] = {}
    total_bytes = 0
    excluded_resolved = tuple(path.resolve() for path in excluded_roots)
    for path in iter_files(root, include_ignored=include_all):
        if any(_inside(path, excluded) for excluded in excluded_resolved):
            continue
        try:
            category, action, reason = classify(path, root)
            size = path.stat().st_size
            file_hash = sha256_file(path)
        except OSError as exc:
            entries.append({
                "path": safe_relative(path, root), "sizeBytes": None, "sha256": "",
                "extension": path.suffix.lower(), "mime": "application/octet-stream",
                "lineCount": None, "category": "unreadable", "packageAction": "repair",
                "reason": f"File could not be read: {type(exc).__name__}: {exc}",
            })
            totals["unreadable"] = totals.get("unreadable", 0) + 1
            continue
        entry = {
            "path": safe_relative(path, root),
            "sizeBytes": size,
            "sha256": file_hash,
            "extension": path.suffix.lower(),
            "mime": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            "lineCount": line_count(path),
            "category": category,
            "packageAction": action,
            "reason": reason,
        }
        entries.append(entry)
        totals[category] = totals.get(category, 0) + 1
        total_bytes += size
    jsonl_path = out_dir / "inventory.jsonl"
    with jsonl_path.open("w", encoding="utf-8", newline="\n") as handle:
        for item in entries:
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
    csv_path = out_dir / "inventory.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(entries[0].keys()) if entries else ["path"])
        writer.writeheader()
        writer.writerows(entries)
    summary = {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "root": root.as_posix(),
        "fileCount": len(entries),
        "totalBytes": total_bytes,
        "categories": totals,
        "includeAll": include_all,
        "inventoryJsonl": jsonl_path.as_posix(),
        "inventoryCsv": csv_path.as_posix(),
    }
    write_json(out_dir / "inventory-summary.json", summary)
    return summary


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False
