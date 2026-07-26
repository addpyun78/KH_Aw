from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .util import load_state, read_json, save_state, sha256_file, utc_now, write_json


def bootstrap_project_runtime(plugin_root: Path, workspace_root: Path, version: str) -> dict[str, Any]:
    source = plugin_root.resolve() / "scripts"
    target = workspace_root.resolve() / "runtime" / version
    if not target.is_dir():
        shutil.copytree(
            source,
            target,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
        )
    files = [
        {"path": path.relative_to(target).as_posix(), "sha256": sha256_file(path)}
        for path in sorted(target.rglob("*")) if path.is_file()
    ]
    receipt = {
        "schemaVersion": "4.0", "createdAt": utc_now(), "version": version,
        "source": source.as_posix(), "runtimeRoot": target.as_posix(), "files": files,
    }
    write_json(workspace_root / "runtime" / "active-runtime.json", receipt)
    return receipt


def resume_run(run_root: Path) -> dict[str, Any]:
    run_root = run_root.resolve()
    state = load_state(run_root)
    stage_status = state.get("stageStatus", {})
    stages = list(stage_status)
    pending = next((stage for stage in stages if not str(stage_status.get(stage, "")).startswith("passed")), None)
    state["currentStage"] = pending or state.get("currentStage", "release")
    state["status"] = "active" if pending else state.get("status", "release-passed-awaiting-receipt")
    history_path = run_root / "events" / "resume-history.json"
    history = read_json(history_path, {"schemaVersion": "4.0", "events": []})
    event = {
        "resumedAt": utc_now(),
        "runId": state.get("runId"),
        "stage": state["currentStage"],
        "activeRepairTicket": state.get("repair", {}).get("activeTicket", ""),
    }
    history["events"].append(event)
    write_json(history_path, history)
    save_state(run_root, state)
    return {"ok": True, "runRoot": run_root.as_posix(), "resume": event, "state": state}
