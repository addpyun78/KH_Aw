from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .util import read_json, sha256_file, utc_now


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser().resolve()


def _manifest(path: Path) -> dict[str, Any]:
    return read_json(path / ".codex-plugin" / "plugin.json", {})


def inspect_installations(plugin_name: str = "kh-aw", home: Path | None = None) -> dict[str, Any]:
    home = (home or codex_home()).resolve()
    roots: list[dict[str, Any]] = []
    candidates: set[Path] = set()
    for base in (home / "plugins" / "cache", home / "plugins", home / "marketplaces"):
        if not base.is_dir():
            continue
        for manifest_path in base.rglob("plugin.json"):
            if manifest_path.parent.name != ".codex-plugin":
                continue
            manifest = read_json(manifest_path, {})
            if manifest.get("name") == plugin_name:
                candidates.add(manifest_path.parent.parent.resolve())
    for root in sorted(candidates, key=lambda value: value.as_posix().lower()):
        manifest = _manifest(root)
        roots.append({
            "root": root.as_posix(),
            "version": str(manifest.get("version", "")),
            "manifestSha256": sha256_file(root / ".codex-plugin" / "plugin.json"),
            "kind": "versioned-cache" if root.parent.name == plugin_name else "plugin-root",
            "hasPackageManifest": (root / "PACKAGE_MANIFEST.json").is_file(),
            "skills": sorted(
                child.name for child in (root / "skills").iterdir()
                if child.is_dir() and (child / "SKILL.md").is_file()
            ) if (root / "skills").is_dir() else [],
        })
    version_groups: dict[str, list[str]] = {}
    for item in roots:
        version_groups.setdefault(item["version"], []).append(item["root"])
    duplicates = [
        {"version": version, "roots": paths}
        for version, paths in sorted(version_groups.items())
        if len(paths) > 1
    ]
    versions = sorted({item["version"] for item in roots if item["version"]})
    return {
        "schemaVersion": "4.0",
        "checkedAt": utc_now(),
        "codexHome": home.as_posix(),
        "plugin": plugin_name,
        "installations": roots,
        "versions": versions,
        "duplicates": duplicates,
        "shadowingRisk": bool(duplicates or len(versions) > 1),
    }


def resolve_active_installation(
    plugin_name: str = "kh-aw",
    home: Path | None = None,
    requested_version: str = "",
) -> dict[str, Any]:
    inventory = inspect_installations(plugin_name, home)
    candidates = inventory["installations"]
    if requested_version:
        candidates = [item for item in candidates if item["version"] == requested_version]
    candidates = sorted(
        candidates,
        key=lambda item: (
            tuple(int(part) for part in item["version"].split(".") if part.isdigit()),
            item["root"],
        ),
        reverse=True,
    )
    selected = candidates[0] if candidates else None
    return {
        **inventory,
        "requestedVersion": requested_version,
        "active": selected,
        "resolution": "highest-matching-version" if selected else "not-found",
        "ambiguous": bool(selected and any(
            item["version"] == selected["version"] and item["root"] != selected["root"]
            for item in candidates
        )),
    }


def skill_visibility(plugin_root: Path) -> dict[str, Any]:
    root = plugin_root.resolve()
    manifest = _manifest(root)
    skills_root = root / str(manifest.get("skills", "./skills")).replace("./", "")
    visible = []
    if skills_root.is_dir():
        for skill_dir in sorted(skills_root.iterdir()):
            skill_file = skill_dir / "SKILL.md"
            if skill_dir.is_dir() and skill_file.is_file():
                text = skill_file.read_text(encoding="utf-8", errors="replace")
                visible.append({
                    "name": skill_dir.name,
                    "path": skill_file.as_posix(),
                    "hasFrontmatter": text.startswith("---\n"),
                })
    return {
        "pluginRoot": root.as_posix(),
        "skillsRoot": skills_root.as_posix(),
        "visibleSkills": visible,
        "singleEntrypoint": len(visible) == 1 and visible[0]["name"] == "kh-aw",
    }
