from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .capabilities import capability_policy
from .contracts import (
    analysis_ledger_template,
    design_ledger_template,
    implementation_ledger_template,
    page_inventory_template,
    release_template,
    remove_forbidden_manual_keys,
    research_plan_template,
    review_template,
    stage_status_passed,
    test_template,
)
from .protection import restore_snapshot
from .run_lock import restore_run_lock
from .tooling import tool_policy
from .orchestration import orchestration_policy, ensure_agent_plan
from .util import read_json, save_state, sha256_file, slug, utc_now, write_json, write_last_good


def failure_signature(stage: str, issues: list[dict[str, Any]]) -> str:
    codes = sorted(str(item.get("code", "")) for item in issues)
    return hashlib.sha256(f"{stage}|{'|'.join(codes)}".encode()).hexdigest()[:16]


def deterministic_repair(run_root: Path, state: dict[str, Any], stage: str, issues: list[dict[str, Any]]) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    codes = {str(item.get("code", "")) for item in issues}
    if any(code.startswith("RUN_LOCK_") for code in codes):
        result = restore_run_lock(run_root, state)
        actions.append({"action": "restore-run-lock", "result": result})
    if "ANALYSIS_FOLDER_MUTATED" in codes:
        result = restore_snapshot(run_root)
        actions.append({"action": "restore-analysis-folder", "result": result})
    if "TARGET_TOOL_POLICY_TAMPERED" in codes or "APK_INSTALL_EXCLUSION_NOT_LOCKED" in codes:
        path = run_root / "contract" / "tool-policy.json"
        write_json(path, tool_policy(state.get("targetPipeline", "web-responsive"), Path(str(state.get("projectRoot", "."))).resolve()))
        actions.append({"action": "restore-tool-policy", "path": path.as_posix()})
    if "NATIVE_CAPABILITY_POLICY_TAMPERED" in codes:
        path = run_root / "contract" / "native-capability-policy.json"
        write_json(path, capability_policy())
        actions.append({"action": "restore-native-capability-policy", "path": path.as_posix()})
    if "SUBAGENT_POLICY_TAMPERED" in codes:
        path = run_root / "contract" / "subagent-orchestration-policy.json"
        write_json(path, orchestration_policy())
        actions.append({"action": "restore-subagent-orchestration-policy", "path": path.as_posix()})
    requirements = read_json(run_root / "contract" / "requirements.json", {})
    defaults = {
        run_root / "contract" / "native-capability-policy.json": capability_policy(),
        run_root / "contract" / "tool-policy.json": tool_policy(state.get("targetPipeline", "web-responsive"), Path(str(state.get("projectRoot", "."))).resolve()),
        run_root / "contract" / "subagent-orchestration-policy.json": orchestration_policy(),
        run_root / "analysis" / "analysis-ledger.json": analysis_ledger_template(),
        run_root / "evidence" / "research-plan.json": research_plan_template(requirements, state.get("targetPipeline", "web-responsive")),
        run_root / "evidence" / "source-registry.json": {"schemaVersion": "3.0", "sources": []},
        run_root / "design" / "page-inventory.json": page_inventory_template(),
        run_root / "design" / "design-ledger.json": design_ledger_template(),
        run_root / "implementation" / "implementation-ledger.json": implementation_ledger_template(),
        run_root / "review" / "review.json": review_template(),
        run_root / "test" / "test-report.json": test_template(),
        run_root / "release" / "release.json": release_template(),
    }
    for path, default in defaults.items():
        value = read_json(path, None)
        if value is None:
            last_good = run_root / "checkpoints" / f"{slug(path.relative_to(run_root).as_posix())}.last-good{path.suffix}"
            if last_good.is_file() and read_json(last_good, None) is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(last_good.read_bytes())
                actions.append({"action": "restore-json-from-last-good", "path": path.as_posix(), "source": last_good.as_posix()})
            else:
                write_json(path, default)
                actions.append({"action": "create-missing-json-template", "path": path.as_posix()})
            continue
        cleaned, removed = remove_forbidden_manual_keys(value)
        if removed:
            write_json(path, cleaned)
            actions.append({"action": "remove-forbidden-manual-design-keys", "path": path.as_posix(), "keys": sorted(set(removed))})
    registry_path = run_root / "evidence" / "source-registry.json"
    registry = read_json(registry_path, {"schemaVersion": "3.0", "sources": []})
    if isinstance(registry, dict):
        unique: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for source in registry.get("sources", []):
            key = (str(source.get("elementId", "")), str(source.get("url", ""))) if isinstance(source, dict) else ("", "")
            if not all(key) or key in seen:
                continue
            seen.add(key)
            unique.append(source)
        if len(unique) != len(registry.get("sources", [])):
            registry["sources"] = unique
            write_json(registry_path, registry)
            actions.append({"action": "deduplicate-source-registry", "remaining": len(unique)})
    subagent_codes = {code for code in codes if code.startswith("SUBAGENT_") or code.startswith("LEAD_AGENT_") or code == "FIXED_SIXTY_SUBAGENTS_FORBIDDEN"}
    if subagent_codes:
        destructive_replan_codes = {
            "SUBAGENT_POLICY_TAMPERED", "SUBAGENT_PLAN_MISSING", "SUBAGENT_COUNT_OUT_OF_RANGE",
            "SUBAGENT_DYNAMIC_SCALE_MISMATCH", "SUBAGENT_ASSIGNMENT_INVALID", "FIXED_SIXTY_SUBAGENTS_FORBIDDEN",
        }
        force_replan = bool(subagent_codes & destructive_replan_codes)
        plan = ensure_agent_plan(run_root, state, stage, force=force_replan)
        actions.append({
            "action": "regenerate-dynamic-subagent-plan" if force_replan else "preserve-valid-subagent-results-and-refresh-dispatch",
            "stage": stage,
            "recommendedSubAgents": plan.get("recommendedSubAgents"),
            "minimum": plan.get("minimumSubAgents"),
            "maximum": plan.get("maximumSubAgents"),
            "preservedExistingWorkerResults": not force_replan,
            "dispatchManifest": (run_root / "orchestration" / stage / "dispatch-manifest.json").as_posix(),
        })
    if "STAGE_ORDER_VIOLATION" in codes:
        for candidate, status in state.get("stageStatus", {}).items():
            if not stage_status_passed(status):
                state["currentStage"] = candidate
                actions.append({"action": "reroute-to-earliest-incomplete-stage", "stage": candidate})
                break
    machine_actions: list[dict[str, Any]] = []
    if any(code.startswith("SUBAGENT_") or code.startswith("LEAD_AGENT_") or code == "FIXED_SIXTY_SUBAGENTS_FORBIDDEN" for code in codes):
        plan = read_json(run_root / "orchestration" / stage / "agent-plan.json", {})
        machine_actions.append({
            "executor": "codex-subagent-orchestrator",
            "mode": "native-/agents-required",
            "stage": stage,
            "requiredWorkerCount": plan.get("recommendedSubAgents", 2),
            "minimum": 2,
            "maximum": 60,
            "dispatchManifest": (run_root / "orchestration" / stage / "dispatch-manifest.json").as_posix(),
            "promptOnlyForbidden": True,
        })
    native_codes = {
        code for code in codes
        if code.startswith("NATIVE_CAPABILITY_") or code in {"NATIVE_SLASH_REQUIRED", "NATIVE_CAPABILITY_SESSION_LINK_INVALID"}
    }
    if native_codes:
        machine_actions.append({
            "executor": "codex-native-slash",
            "mode": "native-session-invocation-required",
            "stage": stage,
            "issueCodes": sorted(native_codes),
            "fallbackAllowed": False,
        })
    if any(code in codes for code in {"TOOL_DISCOVERY_EVIDENCE_MISSING", "TARGET_TOOLCHAIN_COVERAGE_INCOMPLETE", "TOOL_EXECUTIONS_MISSING", "TOOL_EXECUTION_FAILED"}):
        machine_actions.append({"executor": "run-toolchain", "mode": "actual-command-execution", "target": state.get("targetPipeline")})
    if any(code in codes for code in {"ACTUAL_SCREENSHOT_INVALID", "REVIEW_PAGE_COVERAGE_INCOMPLETE", "PAGE_REVIEW_FAILED"}):
        machine_actions.append({"executor": "browser-or-screenshot-test", "mode": "actual-runtime-capture", "apkInstallExcluded": True})
    if "APK_INSTALL_COMMAND_DETECTED" in codes:
        machine_actions.append({"executor": "remove-forbidden-command", "patterns": ["adb install", "installDebug", "connectedAndroidTest", "bundletool install-apks"]})
    next_action = {
        "schemaVersion": "3.0",
        "updatedAt": utc_now(),
        "stage": stage,
        "status": "repairing",
        "issueCodes": sorted(codes),
        "deterministicActions": actions,
        "machineRepairActions": machine_actions,
        "instruction": "Repair the physical root-cause files and evidence, then rerun the same stage. Editing prose alone cannot pass.",
    }
    write_json(run_root / "next-action.json", next_action)
    save_state(run_root, state)
    return {"actions": actions, "deterministicChanges": len(actions), "nextAction": (run_root / "next-action.json").as_posix()}


def create_repair_ticket(run_root: Path, state: dict[str, Any], stage: str, gate: dict[str, Any], deterministic: dict[str, Any]) -> dict[str, Any]:
    signature = failure_signature(stage, gate.get("issues", []))
    repair_state = state.setdefault("repair", {})
    signatures = repair_state.setdefault("signatures", {})
    entry = signatures.setdefault(signature, {"attempt": 0, "strategyGeneration": 1})
    entry["attempt"] += 1
    if entry["attempt"] > 3:
        entry["attempt"] = 1
        entry["strategyGeneration"] += 1
    global_attempt = int(repair_state.get("globalAttempt", 0)) + 1
    repair_state["globalAttempt"] = global_attempt
    ticket_dir = run_root / "repairs" / stage / f"attempt-{global_attempt:03d}"
    ticket_path = ticket_dir / "repair-ticket.json"
    ticket = {
        "schemaVersion": "3.0",
        "createdAt": utc_now(),
        "closedAt": "",
        "runId": state.get("runId"),
        "stage": stage,
        "status": "repair-required-nonterminal",
        "failureSignature": signature,
        "signatureAttempt": entry["attempt"],
        "strategyGeneration": entry["strategyGeneration"],
        "rootCauseRequired": True,
        "rule": 'Do not convert a failed gate into completion. Repair the physical root cause and rerun the same gate.',
        "strategyChangeRequired": entry["strategyGeneration"] > 1,
        "issues": gate.get("issues", []),
        "deterministicRepair": deterministic,
        "repairEvidence": [],
        "closureEvidence": {},
        "requiredEvidence": [
            'physical paths of changed files',
            'SHA-256 before and after repair',
            'rerun verification command and exit code',
            'root-cause explanation proving the same failure will not recur',
        ],
        "nextCommand": f"python3 scripts/kh_aw_cli.py advance --run-root {run_root.as_posix()} --stage {stage}",
    }
    write_json(ticket_path, ticket)
    repair_state["activeTicket"] = ticket_path.as_posix()
    state["status"] = "repairing"
    state["currentStage"] = stage
    save_state(run_root, state)
    return {**ticket, "ticketPath": ticket_path.as_posix()}


def close_stage_tickets(run_root: Path, state: dict[str, Any], stage: str, gate_report_path: Path) -> dict[str, Any]:
    closed: list[str] = []
    stage_root = run_root / "repairs" / stage
    if stage_root.is_dir():
        for path in sorted(stage_root.rglob("repair-ticket.json")):
            ticket = read_json(path, {})
            if ticket.get("status") == "closed":
                continue
            ticket["status"] = "closed"
            ticket["closedAt"] = utc_now()
            ticket["closureEvidence"] = {
                "gateReportPath": gate_report_path.relative_to(run_root).as_posix(),
                "gateReportSha256": sha256_file(gate_report_path),
                "passed": True,
            }
            write_json(path, ticket)
            closed.append(path.relative_to(run_root).as_posix())
    state.setdefault("repair", {})["activeTicket"] = ""
    save_state(run_root, state)
    return {"closedCount": len(closed), "tickets": closed}


def checkpoint_stage(run_root: Path, stage: str, artifact_paths: list[Path]) -> dict[str, Any]:
    checkpoint_root = run_root / "checkpoints" / stage
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    for source in artifact_paths:
        if not source.is_file():
            continue
        target = write_last_good(source, checkpoint_root, source.relative_to(run_root).as_posix())
        files.append({
            "source": source.relative_to(run_root).as_posix(),
            "checkpoint": target.relative_to(run_root).as_posix(),
            "sha256": sha256_file(source),
        })
    manifest = {"schemaVersion": "3.0", "stage": stage, "createdAt": utc_now(), "files": files}
    write_json(checkpoint_root / "checkpoint.json", manifest)
    return manifest
