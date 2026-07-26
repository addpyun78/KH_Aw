from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .distribution import validate_distribution
from .installation import inspect_installations, skill_visibility
from .integrity import validate_package_manifest
from .plugin_validate import validate_marketplace, validate_plugin
from .util import load_state, read_json, sha256_file, utc_now


def _rows(category: str, errors: list[str]) -> list[dict[str, Any]]:
    return [{
        "code": f"{category.upper().replace('-', '_')}_{index:03d}",
        "category": category,
        "status": "failed",
        "expected": "No validation error",
        "actual": message,
        "repair": f"Repair the {category} owner file or root resolution, then rerun doctor.",
        "reverify": "python scripts/kh_aw_cli.py doctor --plugin-root <plugin-root>",
    } for index, message in enumerate(errors, 1)]


def run_doctor(
    plugin_root: Path,
    marketplace_root: Path | None = None,
    *,
    include_distribution: bool = False,
    codex_home: Path | None = None,
) -> dict[str, Any]:
    plugin_root = plugin_root.resolve()
    checks: list[dict[str, Any]] = []
    validators: list[tuple[str, Callable[[], list[str]]]] = [
        ("plugin", lambda: validate_plugin(plugin_root)),
        ("package-integrity", lambda: validate_package_manifest(plugin_root)),
    ]
    if marketplace_root is not None:
        market = marketplace_root.resolve()
        validators.append(("marketplace", lambda: validate_marketplace(market)))
        if include_distribution:
            validators.append(("distribution", lambda: validate_distribution(plugin_root, market)))
    for category, validator in validators:
        errors = validator()
        checks.extend(_rows(category, errors))
        if not errors:
            checks.append({
                "code": f"{category.upper().replace('-', '_')}_OK",
                "category": category,
                "status": "passed",
                "expected": "No validation error",
                "actual": "No validation error",
                "repair": "",
                "reverify": "",
            })
    visibility = skill_visibility(plugin_root)
    if not visibility["singleEntrypoint"]:
        checks.extend(_rows("skill-visibility", [
            f"expected only skills/kh-aw/SKILL.md, found {[item['name'] for item in visibility['visibleSkills']]}"
        ]))
    else:
        checks.append({
            "code": "SKILL_VISIBILITY_OK", "category": "skill-visibility",
            "status": "passed", "expected": "One kh-aw entrypoint",
            "actual": "One kh-aw entrypoint", "repair": "", "reverify": "",
        })
    installs = inspect_installations(home=codex_home)
    failed = [item for item in checks if item["status"] == "failed"]
    return {
        "schemaVersion": "4.0",
        "checkedAt": utc_now(),
        "ok": not failed,
        "pluginRoot": plugin_root.as_posix(),
        "marketplaceRoot": marketplace_root.resolve().as_posix() if marketplace_root else "",
        "mode": "distribution" if include_distribution else "plugin",
        "checks": checks,
        "errors": [item["actual"] for item in failed],
        "installation": installs,
        "skillVisibility": visibility,
    }


def run_project_doctor(run_root: Path) -> dict[str, Any]:
    run_root = run_root.resolve()
    errors: list[str] = []
    try:
        state = load_state(run_root)
    except FileNotFoundError as exc:
        state = {}
        errors.append(str(exc))
    requirements = read_json(run_root / "contract" / "requirements.json", {})
    graph = read_json(run_root / "contract" / "task-graph.json", {})
    reachability = read_json(run_root / "inventory" / "source-reachability.json", {})
    requirement_ids = {
        str(item.get("id")) for item in requirements.get("requirements", [])
        if isinstance(item, dict) and item.get("id")
    }
    graph_ids = {
        str(req_id) for item in graph.get("tickets", []) if isinstance(item, dict)
        for req_id in item.get("requirementIds", [])
    }
    if not requirement_ids or graph_ids != requirement_ids:
        errors.append("task graph does not cover every compiled requirement")
    if not isinstance(reachability.get("nodes"), list):
        errors.append("source reachability inventory is missing")
    runtime = state.get("projectRuntime", {}) if isinstance(state, dict) else {}
    runtime_root = Path(str(runtime.get("runtimeRoot", "")))
    if not runtime_root.is_dir():
        errors.append("project runtime snapshot is missing")
    else:
        for item in runtime.get("files", []):
            path = runtime_root / str(item.get("path", ""))
            if not path.is_file() or sha256_file(path) != item.get("sha256"):
                errors.append(f"project runtime file mismatch: {item.get('path')}")
    checks = _rows("project", errors)
    if not errors:
        checks.append({
            "code": "PROJECT_OK", "category": "project", "status": "passed",
            "expected": "State, task graph, reachability, and runtime are consistent",
            "actual": "State, task graph, reachability, and runtime are consistent",
            "repair": "", "reverify": "",
        })
    return {
        "schemaVersion": "4.0", "checkedAt": utc_now(), "ok": not errors,
        "runRoot": run_root.as_posix(), "checks": checks, "errors": errors,
    }
