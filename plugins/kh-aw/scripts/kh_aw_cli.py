#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import shutil
import subprocess
import sys
sys.dont_write_bytecode = True
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from kh_aw.capabilities import record_capability
from kh_aw.contracts import STAGES, create_run_contracts, stage_status_passed
from kh_aw.evidence import fetch_url_to_evidence, register_source
from kh_aw.distribution import validate_distribution
from kh_aw.gates import run_gate
from kh_aw.inventory import build_inventory
from kh_aw.page_inventory import build_page_candidates
from kh_aw.integrity import build_package_manifest, validate_package_manifest
from kh_aw.plugin_validate import validate_marketplace, validate_plugin
from kh_aw.doctor import run_doctor, run_project_doctor
from kh_aw.installation import inspect_installations, resolve_active_installation
from kh_aw.packaging import build_deterministic_zip, build_release_manifest
from kh_aw.reachability import analyze_source_reachability
from kh_aw.runtime import bootstrap_project_runtime, resume_run
from kh_aw.versioning import version_ledger
from kh_aw.e2e import run_local_e2e
from kh_aw.verifier import verify_run
from kh_aw.orchestration import (
    ensure_agent_plan, record_subagent_result, record_lead_aggregation,
    canonical_agent_plan, orchestration_issues,
)
from kh_aw.protection import create_protected_snapshot
from kh_aw.run_lock import write_run_lock
from kh_aw.repair import checkpoint_stage, close_stage_tickets, create_repair_ticket, deterministic_repair
from kh_aw.security import scan_release_root
from kh_aw.session_forensics import build_session_forensics
from kh_aw.targeting import infer_target_pipeline
from kh_aw.tooling import (
    bootstrap_tooling,
    command_forbidden,
    discover_tools,
    execute_tool,
    exercise_capability,
    required_tool_ids,
    suggested_commands,
)
from kh_aw.util import (
    is_inside,
    latest_run,
    load_state,
    read_json,
    safe_resolve,
    save_state,
    sha256_file,
    slug,
    utc_now,
    write_json,
)

ENGINE_VERSION = "4.0.0"
STAGE_ARTIFACTS = {
    "intake": ["contract/user-instructions.txt", "contract/requirements.json"],
    "analyze": ["inventory/inventory-summary.json", "inventory/inventory.jsonl", "inventory/inventory.csv", "inventory/page-candidates.json", "analysis/analysis-ledger.json"],
    "research": ["evidence/research-plan.json", "evidence/source-registry.json"],
    "design": ["design/page-inventory.json", "design/design-ledger.json"],
    "implement": ["implementation/implementation-ledger.json"],
    "review": ["review/review.json"],
    "test": ["test/test-report.json"],
    "release": ["release/release.json"],
}


def emit(payload: dict[str, Any], pretty: bool = True) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None))


def resolve_run(args: argparse.Namespace) -> Path:
    if getattr(args, "run_root", None):
        return safe_resolve(args.run_root)
    project = safe_resolve(getattr(args, "project_root", "."))
    workspace = safe_resolve(getattr(args, "workspace_root", project / ".kh_aw"), project)
    return latest_run(workspace)


def earliest_incomplete(state: dict[str, Any]) -> str | None:
    for stage in STAGES:
        if not stage_status_passed(state.get("stageStatus", {}).get(stage, "")):
            return stage
    return None


def _stage_artifacts(run_root: Path, stage: str) -> list[Path]:
    paths = [run_root / relative for relative in STAGE_ARTIFACTS.get(stage, [])]
    paths.extend([
        run_root / "orchestration" / stage / "agent-plan.json",
        run_root / "orchestration" / stage / "dispatch-manifest.json",
        run_root / "orchestration" / stage / "execution-ledger.json",
        run_root / "orchestration" / stage / "lead-aggregation.json",
    ])
    return paths


def _pass_stage(run_root: Path, state: dict[str, Any], stage: str, status: str, gate: dict[str, Any]) -> dict[str, Any]:
    state["stageStatus"][stage] = status
    index = STAGES.index(stage)
    next_stage = STAGES[index + 1] if index + 1 < len(STAGES) else None
    state["currentStage"] = next_stage or "release"
    state["status"] = "active" if next_stage else "release-passed-awaiting-receipt"
    if next_stage:
        ensure_agent_plan(run_root, state, next_stage, force=True)
    gate_path = run_root / "reports" / f"gate-{stage}.json"
    closed = close_stage_tickets(run_root, state, stage, gate_path)
    checkpoint = checkpoint_stage(run_root, stage, _stage_artifacts(run_root, stage))
    write_json(run_root / "next-action.json", {
        "schemaVersion": "3.0", "updatedAt": utc_now(), "stage": next_stage,
        "status": "awaiting-release-receipt" if next_stage is None else "active",
        "instruction": 'All stages passed.' if next_stage is None else f"'Create physical evidence for the next stage ('{next_stage}'), then run advance.'",
    })
    save_state(run_root, state)
    return {"nextStage": next_stage, "closedTickets": closed, "checkpoint": checkpoint, "gate": gate}




def _exercise_stage_capabilities(run_root: Path, state: dict[str, Any], stage: str) -> list[dict[str, Any]]:
    policy = read_json(run_root / "contract" / "native-capability-policy.json", {})
    records = {str(item.get("capabilityId")): item for item in policy.get("records", []) if isinstance(item, dict)}
    results: list[dict[str, Any]] = []
    for definition in policy.get("capabilities", []):
        if not isinstance(definition, dict) or definition.get("stage") != stage or definition.get("required") is not True:
            continue
        capability_id = str(definition.get("id", ""))
        existing = records.get(capability_id)
        if isinstance(existing, dict) and existing.get("mode") == "native" and existing.get("status") == "verified":
            continue
        if policy.get("requiredEvidenceMode") == "native":
            results.append({
                "capabilityId": capability_id,
                "status": "native-unavailable",
                "preferredSlash": definition.get("preferredSlash"),
                "reason": "The active Codex stage owner must use the slash command and register native evidence.",
            })
            continue
        try:
            results.append(exercise_capability(run_root, state, capability_id))
        except Exception as exc:
            results.append({"capabilityId": capability_id, "status": "fallback-failed", "error": str(exc)})
    return results


def cmd_init(args: argparse.Namespace) -> int:
    requested_project = safe_resolve(args.project_root)
    analysis_folder = safe_resolve(args.analysis_folder, requested_project) if args.analysis_folder else None
    if analysis_folder and not analysis_folder.is_dir():
        raise FileNotFoundError(f"analysis folder does not exist: {analysis_folder}")

    if analysis_folder and is_inside(requested_project, analysis_folder):
        if args.output_root:
            project_root = safe_resolve(args.output_root, requested_project) / "product"
        else:
            project_root = analysis_folder.parent / f"{analysis_folder.name}_KH_Aw_Product"
    else:
        project_root = requested_project
    project_root.mkdir(parents=True, exist_ok=True)

    if args.output_root:
        output_base = safe_resolve(args.output_root, project_root)
        workspace_root = output_base / ".kh_aw" if output_base.name != ".kh_aw" else output_base
    else:
        workspace_root = project_root / ".kh_aw"
    workspace_root = workspace_root.resolve()
    if analysis_folder and (is_inside(workspace_root, analysis_folder) or is_inside(project_root, analysis_folder)):
        raise ValueError("project/output/workspace root must not be inside the provided analysis folder")

    instructions_file = safe_resolve(args.instructions_file, requested_project)
    instructions = instructions_file.read_text(encoding="utf-8")
    inferred_target = infer_target_pipeline(instructions, analysis_folder or requested_project)
    target = args.target
    if args.target_auto or args.target == "unknown-needs-confirmation":
        target = str(inferred_target["targetPipeline"])
    if target == "unknown-needs-confirmation":
        raise ValueError("targetPipeline could not be inferred; rerun init with an explicit --target")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{stamp}-{slug(args.name or project_root.name)}"
    run_root = workspace_root / "runs" / run_id
    if run_root.exists():
        raise FileExistsError(run_root)
    run_root.mkdir(parents=True)
    internal_instructions = run_root / "contract" / "user-instructions.txt"
    internal_instructions.parent.mkdir(parents=True, exist_ok=True)
    internal_instructions.write_text(instructions, encoding="utf-8", newline="\n")
    contracts = create_run_contracts(run_root, instructions, target)
    source_root = analysis_folder or project_root
    inventory = build_inventory(source_root, run_root / "inventory", include_all=True, excluded_roots=(workspace_root,))
    page_candidates = build_page_candidates(source_root, run_root / "inventory" / "page-candidates.json")
    reachability = analyze_source_reachability(source_root)
    write_json(run_root / "inventory" / "source-reachability.json", reachability)
    protection = create_protected_snapshot(analysis_folder, run_root) if analysis_folder else None
    state = {
        "schemaVersion": "3.0",
        "engine": "KH_Aw",
        "engineVersion": ENGINE_VERSION,
        "runId": run_id,
        "createdAt": utc_now(),
        "updatedAt": utc_now(),
        "status": "active",
        "currentStage": "intake",
        "projectRoot": project_root.as_posix(),
        "workspaceRoot": workspace_root.as_posix(),
        "runRoot": run_root.as_posix(),
        "analysisMode": "analysis-folder-provided" if analysis_folder else "analysis-folder-not-provided",
        "analysisFolder": analysis_folder.as_posix() if analysis_folder else "",
        "analysisSourceRoot": source_root.as_posix(),
        "instructionsFile": internal_instructions.as_posix(),
        "targetPipeline": target,
        "targetInference": inferred_target,
        "stageStatus": {stage: "pending" for stage in STAGES},
        "contracts": contracts,
        "inventory": inventory,
        "pageCandidates": {
            "path": (run_root / "inventory" / "page-candidates.json").as_posix(),
            "candidateCount": page_candidates.get("candidateCount", 0),
        },
        "sourceReachability": (run_root / "inventory" / "source-reachability.json").as_posix(),
        "protection": {"enabled": bool(protection), "archive": protection.get("archive") if protection else ""},
        "repair": {"globalAttempt": 0, "signatures": {}, "activeTicket": ""},
    }
    state["projectRuntime"] = bootstrap_project_runtime(SCRIPT_ROOT.parent, workspace_root, ENGINE_VERSION)
    write_run_lock(run_root, state)
    save_state(run_root, state)
    ensure_agent_plan(run_root, state, "intake", force=True)
    write_json(workspace_root / "latest-run.json", {"runId": run_id, "runRoot": run_root.as_posix(), "updatedAt": utc_now()})
    bootstrap_tooling(run_root, state)
    _exercise_stage_capabilities(run_root, state, "intake")
    intake = run_gate(run_root, state, "intake", enforce_order=False)
    if intake["pass"]:
        passed = _pass_stage(run_root, state, "intake", "passed", intake)
        status = "initialized-intake-passed"
    else:
        deterministic = deterministic_repair(run_root, state, "intake", intake.get("issues", []))
        second = run_gate(run_root, state, "intake", enforce_order=False)
        if second["pass"]:
            passed = _pass_stage(run_root, state, "intake", "passed-after-deterministic-repair", second)
            status = "initialized-intake-passed-after-auto-repair"
        else:
            ticket = create_repair_ticket(run_root, state, "intake", second, deterministic)
            state["stageStatus"]["intake"] = "repairing"
            save_state(run_root, state)
            passed = {"ticket": ticket, "gate": second}
            status = "initialized-repair-required-nonterminal"
    initialized_ok = not status.endswith("repair-required-nonterminal")
    emit({
        "ok": initialized_ok,
        "status": status,
        "runRoot": run_root.as_posix(),
        "projectRoot": project_root.as_posix(),
        "targetPipeline": target,
        "targetInference": inferred_target,
        "analysisMode": state["analysisMode"],
        "analysisFolderProtected": bool(protection),
        "inventoryFileCount": inventory.get("fileCount"),
        "stageResult": passed,
    })
    return 0 if initialized_ok else 1


def cmd_status(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    state = load_state(run_root)
    reports = {}
    for stage in STAGES:
        report = read_json(run_root / "reports" / f"gate-{stage}.json", None)
        if report:
            reports[stage] = {"pass": report.get("pass"), "issueCount": report.get("issueCount"), "checkedAt": report.get("checkedAt")}
    receipt_check = {"required": state.get("status") == "complete", "valid": None, "issues": []}
    if receipt_check["required"]:
        receipt_path = run_root / "release" / "release-receipt.json"
        receipt = read_json(receipt_path, None)
        if not isinstance(receipt, dict):
            receipt_check["issues"].append("release receipt is missing")
        else:
            if receipt.get("status") != "complete" or receipt.get("runId") != state.get("runId"):
                receipt_check["issues"].append("release receipt identity or status is invalid")
            if state.get("releaseReceiptSha256") != sha256_file(receipt_path):
                receipt_check["issues"].append("release receipt hash does not match state")
            if any(not stage_status_passed(state.get("stageStatus", {}).get(stage, "")) for stage in STAGES):
                receipt_check["issues"].append("one or more current stage states are not exact approved passed statuses")
            if len(receipt.get("gateReports", [])) != len(STAGES):
                receipt_check["issues"].append("release receipt does not contain exactly eight gate bindings")
            for stage in STAGES:
                report_path = run_root / "reports" / f"gate-{stage}.json"
                report = read_json(report_path, None)
                receipt_row = next((row for row in receipt.get("gateReports", []) if row.get("stage") == stage), None)
                if not isinstance(report, dict) or report.get("pass") is not True or report.get("issueCount") != 0:
                    receipt_check["issues"].append(f"{stage} gate is not a clean pass")
                elif not isinstance(receipt_row, dict) or receipt_row.get("sha256") != sha256_file(report_path):
                    receipt_check["issues"].append(f"{stage} gate hash is not bound to the receipt")
        receipt_check["valid"] = not receipt_check["issues"]
    emit({
        "runRoot": run_root.as_posix(),
        "state": state,
        "gateSummary": reports,
        "completionReceipt": receipt_check,
        "nextAction": read_json(run_root / "next-action.json", {}),
    })
    return 0 if receipt_check["valid"] is not False else 1


def cmd_gate(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    state = load_state(run_root)
    result = run_gate(run_root, state, args.stage, enforce_order=not args.ignore_order)
    emit(result)
    return 0 if result["pass"] else 1


def _ensure_design_mockup_render(run_root: Path, state: dict[str, Any]) -> dict[str, Any] | None:
    ledger = read_json(run_root / "design" / "design-ledger.json", {})
    pages = ledger.get("pages", []) if isinstance(ledger, dict) else []
    if not pages:
        return None
    missing = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        screenshot = Path(str(page.get("screenshotPath", "")))
        screenshot = screenshot if screenshot.is_absolute() else run_root / screenshot
        if not screenshot.is_file() or screenshot.stat().st_size < 1000:
            missing.append(str(page.get("pageId", "")))
    if not missing:
        return None
    plugin_root = SCRIPT_ROOT.parent
    if not (plugin_root / "node_modules").is_dir():
        execute_tool(run_root, state, tool_id="kh-aw-tooling-npm-install", command="npm install", cwd=plugin_root, timeout=1800)
        execute_tool(run_root, state, tool_id="kh-aw-playwright-browser-install", command="npx playwright install chromium", cwd=plugin_root, timeout=1800)
    command = f"node {json.dumps(str(SCRIPT_ROOT / 'render_mockups.mjs'))} --run-root {json.dumps(str(run_root))}"
    record = execute_tool(
        run_root,
        state,
        tool_id="design-every-page-mockup-render",
        command=command,
        cwd=plugin_root,
        timeout=900,
        artifacts=[str(run_root / "design" / "screenshots")],
    )
    ledger = read_json(run_root / "design" / "design-ledger.json", {})
    for page in ledger.get("pages", []):
        if not isinstance(page, dict):
            continue
        mockup = Path(str(page.get("mockupPath", "")))
        mockup = mockup if mockup.is_absolute() else run_root / mockup
        screenshot = Path(str(page.get("screenshotPath", "")))
        screenshot = screenshot if screenshot.is_absolute() else run_root / screenshot
        if mockup.is_file():
            page["mockupSha256"] = sha256_file(mockup)
        if screenshot.is_file():
            page["screenshotSha256"] = sha256_file(screenshot)
    board = ledger.get("visualStructureBoard", {})
    board_html = Path(str(board.get("htmlPath", "")))
    board_html = board_html if board_html.is_absolute() else run_root / board_html
    board_image = Path(str(board.get("imagePath", "")))
    board_image = board_image if board_image.is_absolute() else run_root / board_image
    if board_html.is_file(): board["htmlSha256"] = sha256_file(board_html)
    if board_image.is_file(): board["imageSha256"] = sha256_file(board_image)
    write_json(run_root / "design" / "design-ledger.json", ledger)
    return record


def _refresh_review_from_browser(run_root: Path) -> dict[str, Any] | None:
    browser_path = run_root / "test" / "browser" / "chromium" / "result.json"
    if not browser_path.is_file():
        return None
    browser = read_json(browser_path, {})
    report = read_json(run_root / "test" / "test-report.json", {})
    chromium_execution_ids = [
        str(item.get("executionId")) for item in report.get("toolExecutions", [])
        if isinstance(item, dict) and item.get("exitCode") == 0 and "web-playwright-chromium" in item.get("satisfiesToolIds", [item.get("toolId")])
    ]
    design = read_json(run_root / "design" / "design-ledger.json", {})
    design_map = {str(item.get("pageId")): item for item in design.get("pages", []) if isinstance(item, dict)}
    existing_review = read_json(run_root / "review" / "review.json", {})
    if existing_review.get("decision") == "approved" and existing_review.get("pages"):
        return existing_review
    pages = []
    all_pass = True
    for page in browser.get("pages", []):
        page_id = str(page.get("pageId", ""))
        spec = design_map.get(page_id, {})
        mobile = next((item for item in page.get("viewports", []) if item.get("id") == "mobile"), None)
        screenshot = Path(str(mobile.get("screenshot", ""))) if isinstance(mobile, dict) else Path()
        page_pass = bool(mobile and all(item.get("pass") is True for item in page.get("viewports", [])))
        if not screenshot.is_file():
            page_pass = False
        all_pass = all_pass and page_pass
        pages.append({
            "pageId": page_id,
            "actualScreenshotPath": screenshot.resolve().relative_to(run_root.resolve()).as_posix() if screenshot.is_file() else "",
            "actualScreenshotSha256": sha256_file(screenshot) if screenshot.is_file() else "",
            "mockupPath": str(spec.get("mockupPath", "")),
            "structureMatched": False,
            "fieldsMatched": False,
            "logicMatched": False,
            "featuresMatched": False,
            "imagesMatched": page_pass and not page.get("brokenImages"),
            "heroMatched": False,
            "motionMatched": False,
            "typographyMatched": False,
            "colorMatched": False,
            "iconMatched": False,
            "koreanUiMatched": False,
            "statesMatched": False,
            "overlapFree": page_pass,
            "responsivePass": page_pass,
            "accessibilityPass": page_pass and all(item.get("severeCount", 1) == 0 for item in page.get("axe", [])),
            "issues": [{"severity": "major", "status": "open", "message": "Independent semantic and visual comparison is required."}],
            "pass": False,
            "evidencePath": browser_path.relative_to(run_root).as_posix(),
            "evidenceSha256": sha256_file(browser_path),
            "toolExecutionIds": chromium_execution_ids,
            "implementationGatePath": "reports/gate-implement.json",
            "implementationGateSha256": sha256_file(run_root / "reports" / "gate-implement.json") if (run_root / "reports" / "gate-implement.json").is_file() else "",
        })
    review = existing_review
    review["pages"] = pages
    review["crossPageConsistency"] = [{
        "id": "browser-runtime-cross-page",
        "pass": all_pass and len(pages) == len(design_map),
        "evidencePath": browser_path.relative_to(run_root).as_posix(),
        "evidenceSha256": sha256_file(browser_path),
        "toolExecutionIds": chromium_execution_ids,
    }]
    review["unresolvedIssues"] = [{"severity": "major", "status": "open", "message": "Independent page-by-page semantic and visual review has not been registered."}]
    review["decision"] = "pending"
    write_json(run_root / "review" / "review.json", review)
    return review


def _automatic_stage_tools(run_root: Path, state: dict[str, Any], stage: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    target = str(state.get("targetPipeline", "web-responsive"))
    if stage == "design":
        try:
            rendered = _ensure_design_mockup_render(run_root, state)
            if rendered:
                results.append(rendered)
        except Exception as exc:
            results.append({"toolId": "design-every-page-mockup-render", "status": "failed", "error": str(exc)})
    if stage == "review" and target in {"web-responsive", "app-mobile-webview", "cross-platform"}:
        try:
            ns = argparse.Namespace(run_root=str(run_root), tool_id=["web-playwright-chromium"], timeout=900, strict=False)
            cmd_run_toolchain(ns)
            review = _refresh_review_from_browser(run_root)
            results.append({"toolId": "review-browser-auto", "status": "passed" if review and review.get("decision") == "approved" else "failed"})
        except Exception as exc:
            results.append({"toolId": "review-browser-auto", "status": "failed", "error": str(exc)})
    if stage == "test":
        try:
            ns = argparse.Namespace(run_root=str(run_root), tool_id=None, timeout=1800, strict=False)
            cmd_run_toolchain(ns)
            results.append({"toolId": "target-toolchain-auto", "status": "executed"})
        except Exception as exc:
            results.append({"toolId": "target-toolchain-auto", "status": "failed", "error": str(exc)})
    return results


def cmd_advance(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    state = load_state(run_root)
    expected_stage = earliest_incomplete(state)
    requested = args.stage or state.get("currentStage") or expected_stage
    stage = expected_stage or requested
    if requested != stage:
        state["currentStage"] = stage
        state["status"] = "repairing"
        save_state(run_root, state)
        order_gate = {
            "schemaVersion": "3.0", "checkedAt": utc_now(), "stage": requested, "pass": False, "issueCount": 1,
            "issues": [{"code": "STAGE_ORDER_VIOLATION", "severity": "major", "message": 'Previous-stage bypass was blocked.', "evidence": {"requestedStage": requested, "routedStage": stage}}],
        }
        deterministic = deterministic_repair(run_root, state, stage, order_gate["issues"])
        ticket = create_repair_ticket(run_root, state, stage, order_gate, deterministic)
        emit({"ok": False, "status": "repair-required-nonterminal", "requestedStage": requested, "stage": stage, "ticket": ticket, "gate": order_gate})
        return 1

    ensure_agent_plan(run_root, state, stage, force=False)
    _automatic_stage_tools(run_root, state, stage)
    _exercise_stage_capabilities(run_root, state, stage)
    result = run_gate(run_root, state, stage, enforce_order=True)
    if result["pass"]:
        passed = _pass_stage(run_root, state, stage, "passed", result)
        if stage == "release":
            receipt = create_release_receipt(run_root, state)
            _mark_run_complete(run_root, state, receipt)
            passed["releaseReceipt"] = receipt
        emit({"ok": True, "status": "stage-passed", "stage": stage, **passed})
        return 0

    deterministic = deterministic_repair(run_root, state, stage, result.get("issues", []))
    _automatic_stage_tools(run_root, state, stage)
    _exercise_stage_capabilities(run_root, state, stage)
    second = run_gate(run_root, state, stage, enforce_order=True)
    if second["pass"]:
        passed = _pass_stage(run_root, state, stage, "passed-after-deterministic-repair", second)
        if stage == "release":
            receipt = create_release_receipt(run_root, state)
            _mark_run_complete(run_root, state, receipt)
            passed["releaseReceipt"] = receipt
        emit({"ok": True, "status": "stage-passed-after-auto-repair", "stage": stage, "repair": deterministic, **passed})
        return 0

    ticket = create_repair_ticket(run_root, state, stage, second, deterministic)
    state["stageStatus"][stage] = "repairing"
    save_state(run_root, state)
    emit({
        "ok": False,
        "status": "repair-required-nonterminal",
        "stage": stage,
        "message": 'The stage remains blocked. Repair the physical root-cause files and evidence, then rerun the same advance command.',
        "ticket": ticket,
        "gate": second,
    })
    return 1


def create_release_receipt(run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    gate_files = []
    for stage in STAGES:
        path = run_root / "reports" / f"gate-{stage}.json"
        report = read_json(path, None)
        if not path.is_file() or not isinstance(report, dict):
            raise RuntimeError(f"release receipt blocked: missing gate report for {stage}")
        if report.get("stage") != stage or report.get("pass") is not True or report.get("issueCount") != 0 or report.get("issues") != []:
            raise RuntimeError(f"release receipt blocked: {stage} gate is not a clean pass")
        if not stage_status_passed(state.get("stageStatus", {}).get(stage, "")):
            raise RuntimeError(f"release receipt blocked: {stage} state is not an approved passed status")
        gate_files.append({
            "stage": stage,
            "path": path.relative_to(run_root).as_posix(),
            "sha256": sha256_file(path),
            "pass": True,
            "issueCount": 0,
        })
    receipt = {
        "schemaVersion": "3.0",
        "createdAt": utc_now(),
        "runId": state.get("runId"),
        "engineVersion": state.get("engineVersion"),
        "status": "complete",
        "stageStatus": state.get("stageStatus"),
        "gateReports": gate_files,
        "subAgentOrchestration": [
            {
                "stage": stage,
                "planPath": f"orchestration/{stage}/agent-plan.json",
                "planSha256": sha256_file(run_root / "orchestration" / stage / "agent-plan.json") if (run_root / "orchestration" / stage / "agent-plan.json").is_file() else "",
                "ledgerPath": f"orchestration/{stage}/execution-ledger.json",
                "ledgerSha256": sha256_file(run_root / "orchestration" / stage / "execution-ledger.json") if (run_root / "orchestration" / stage / "execution-ledger.json").is_file() else "",
                "aggregationPath": f"orchestration/{stage}/lead-aggregation.json",
                "aggregationSha256": sha256_file(run_root / "orchestration" / stage / "lead-aggregation.json") if (run_root / "orchestration" / stage / "lead-aggregation.json").is_file() else "",
            }
            for stage in STAGES
        ],
        "analysisMode": state.get("analysisMode"),
        "projectRoot": state.get("projectRoot"),
        "rule": "The engine creates this receipt only after all eight physical gates pass with zero issues.",
    }
    path = run_root / "release" / "release-receipt.json"
    write_json(path, receipt)
    receipt["path"] = path.as_posix()
    receipt["sha256"] = sha256_file(path)
    return receipt


def _mark_run_complete(run_root: Path, state: dict[str, Any], receipt: dict[str, Any]) -> None:
    receipt_path = Path(str(receipt.get("path", "")))
    if not receipt_path.is_file() or receipt.get("sha256") != sha256_file(receipt_path):
        raise RuntimeError("run completion blocked: release receipt is missing or changed")
    state["status"] = "complete"
    state["currentStage"] = "release"
    state["releaseReceiptPath"] = receipt_path.as_posix()
    state["releaseReceiptSha256"] = receipt["sha256"]
    save_state(run_root, state)
    write_json(run_root / "next-action.json", {
        "schemaVersion": "3.0",
        "updatedAt": utc_now(),
        "stage": None,
        "status": "complete",
        "instruction": "All stages passed and the immutable release receipt was created.",
    })


def cmd_finalize(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    state = load_state(run_root)
    failed = []
    for stage in STAGES:
        _exercise_stage_capabilities(run_root, state, stage)
        result = run_gate(run_root, state, stage, enforce_order=False)
        if not result["pass"]:
            failed.append(result)
    if failed:
        owner = failed[0]["stage"]
        deterministic = deterministic_repair(run_root, state, owner, failed[0].get("issues", []))
        ticket = create_repair_ticket(run_root, state, owner, failed[0], deterministic)
        state["stageStatus"][owner] = "repairing"
        save_state(run_root, state)
        emit({"ok": False, "status": "repair-required-nonterminal", "stage": owner, "failedStages": [item["stage"] for item in failed], "ticket": ticket})
        return 1
    for stage in STAGES:
        state["stageStatus"][stage] = "passed-final-verification"
    state["status"] = "release-passed-awaiting-receipt"
    state["currentStage"] = "release"
    save_state(run_root, state)
    receipt = create_release_receipt(run_root, state)
    _mark_run_complete(run_root, state, receipt)
    emit({"ok": True, "status": "complete", "receipt": receipt})
    return 0


def cmd_prepare_agents(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    state = load_state(run_root)
    justification = safe_resolve(args.justification_file, run_root) if args.justification_file else None
    plan = ensure_agent_plan(
        run_root, state, args.stage, force=args.force,
        selected_count=args.count, justification_file=justification,
    )
    emit({
        "ok": True,
        "stage": args.stage,
        "recommendedSubAgents": plan.get("recommendedSubAgents"),
        "minimum": plan.get("minimumSubAgents"),
        "maximum": plan.get("maximumSubAgents"),
        "planPath": (run_root / "orchestration" / args.stage / "agent-plan.json").as_posix(),
        "dispatchPath": (run_root / "orchestration" / args.stage / "dispatch-manifest.json").as_posix(),
        "assignments": plan.get("assignments", []),
    })
    return 0


def cmd_record_subagent(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    record = record_subagent_result(
        run_root,
        stage=args.stage,
        worker_id=args.worker_id,
        session_id=args.session_id,
        invocation=args.invocation,
        invocation_receipt_file=safe_resolve(args.invocation_receipt_file, run_root),
        session_evidence_file=safe_resolve(args.session_evidence_file),
        evidence_file=safe_resolve(args.evidence_file, run_root),
        review_of_worker_ids=args.review_of or [],
        task_id=args.task_id or "",
        delegation_mode=args.delegation_mode,
    )
    emit({"ok": True, "subagent": record})
    return 0


def cmd_aggregate_agents(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    plan = read_json(run_root / "orchestration" / args.stage / "agent-plan.json", {})
    accepted = args.accepted_worker_id or [
        str(item.get("workerId")) for item in plan.get("assignments", []) if isinstance(item, dict) and item.get("workerId")
    ]
    aggregation = record_lead_aggregation(
        run_root,
        stage=args.stage,
        lead_agent_id=args.lead_agent_id,
        lead_session_id=args.lead_session_id,
        session_evidence_file=safe_resolve(args.session_evidence_file),
        evidence_file=safe_resolve(args.evidence_file, run_root),
        accepted_worker_ids=accepted,
        resolved_conflicts=args.resolved_conflict or [],
    )
    emit({"ok": True, "aggregation": aggregation})
    return 0


def cmd_agent_status(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    state = load_state(run_root)
    plan = ensure_agent_plan(run_root, state, args.stage, force=False)
    ledger = read_json(run_root / "orchestration" / args.stage / "execution-ledger.json", {})
    aggregation = read_json(run_root / "orchestration" / args.stage / "lead-aggregation.json", {})
    issues = orchestration_issues(run_root, state, args.stage)
    emit({
        "ok": not issues,
        "stage": args.stage,
        "planned": plan.get("recommendedSubAgents", 0),
        "completed": len(ledger.get("workers", [])),
        "aggregationStatus": aggregation.get("status", "missing"),
        "issues": issues,
    })
    return 0 if not issues else 1


def cmd_register_source(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    record = register_source(
        run_root,
        element_id=args.element_id,
        source_type=args.source_type,
        url=args.url,
        body_file=safe_resolve(args.body_file),
        title=args.title or "",
        query=args.query or "",
        http_status=args.http_status,
        project_fit_reason=args.project_fit_reason or "",
        license_note=args.license_note or "",
        retrieval_mode="native-browser-extraction",
        retrieval_session_id=args.session_id,
        retrieval_evidence_file=safe_resolve(args.retrieval_evidence_file, run_root),
    )
    accepted = record.get("accepted") is True
    emit({"ok": accepted, "source": record})
    return 0 if accepted else 1


def cmd_fetch_source(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    record = fetch_url_to_evidence(
        run_root,
        element_id=args.element_id,
        source_type=args.source_type,
        url=args.url,
        query=args.query or "",
        project_fit_reason=args.project_fit_reason or "",
        license_note=args.license_note or "",
        timeout=args.timeout,
    )
    accepted = record.get("accepted") is True
    emit({"ok": accepted, "source": record})
    return 0 if accepted else 1


def cmd_record_command(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    state = load_state(run_root)
    required_ids = set(required_tool_ids(
        str(state.get("targetPipeline", "web-responsive")),
        Path(str(state.get("projectRoot", "."))).resolve(),
    ))
    if (args.tool_id or "custom-command") in required_ids:
        raise ValueError(
            f"{args.tool_id} is a required tool and must be executed through run-toolchain"
        )
    record = execute_tool(
        run_root,
        state,
        tool_id=args.tool_id or "custom-command",
        command=args.command,
        cwd=safe_resolve(args.cwd, Path(str(state.get("projectRoot", ".")))) if args.cwd else None,
        timeout=args.timeout,
        artifacts=args.artifact or [],
    )
    emit({"ok": record["exitCode"] == 0, "execution": record})
    return 0 if record["exitCode"] == 0 else max(1, int(record["exitCode"]))


def cmd_bootstrap_tools(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    state = load_state(run_root)
    result = bootstrap_tooling(run_root, state)
    report_path = run_root / "test" / "test-report.json"
    report = read_json(report_path, {})
    report["toolDiscovery"] = {
        "path": result["discovery"]["path"],
        "sha256": result["discovery"]["sha256"],
    }
    report["apkInstallationPolicy"] = "forbidden"
    write_json(report_path, report)
    emit({"ok": True, **result})
    return 0


def cmd_configure_tools(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    policy_path = run_root / "contract" / "tool-policy.json"
    policy = read_json(policy_path, {})
    config = policy.setdefault("configuration", {})
    for key, value in {
        "baseUrl": args.base_url,
        "startCommand": args.start_command,
        "serverReadyUrl": args.server_ready_url,
        "androidAvd": args.android_avd,
        "androidSerial": args.android_serial,
        "iosDevice": args.ios_device,
    }.items():
        if value is not None:
            config[key] = value
    commands = config.setdefault("commands", {})
    for raw in args.command or []:
        if "=" not in raw:
            raise ValueError("--command must be TOOL_ID=COMMAND")
        tool_id, command = raw.split("=", 1)
        if command_forbidden(command):
            raise ValueError(f"forbidden APK installation command for {tool_id}")
        commands[tool_id.strip()] = command.strip()
    write_json(policy_path, policy)
    emit({"ok": True, "toolPolicy": policy})
    return 0


def cmd_record_native(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    evidence = safe_resolve(args.evidence_file, run_root)
    record = record_capability(
        run_root,
        capability_id=args.capability_id,
        mode="native",
        evidence_file=evidence,
        invocation=args.invocation,
        tool_execution_ids=args.tool_execution_id or [],
        session_id=args.session_id or "",
        session_evidence_file=safe_resolve(args.session_evidence_file),
    )
    emit({"ok": True, "record": record})
    return 0


def cmd_exercise_native(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    state = load_state(run_root)
    policy = read_json(run_root / "contract" / "native-capability-policy.json", {})
    required_ids = {
        str(item.get("id"))
        for item in policy.get("capabilities", [])
        if isinstance(item, dict) and item.get("required") is True
    }
    if args.capability_id in required_ids and policy.get("requiredEvidenceMode") == "native":
        raise ValueError(
            f"{args.capability_id} requires native Codex slash evidence; exercise-native cannot satisfy this gate"
        )
    record = exercise_capability(run_root, state, args.capability_id)
    emit({"ok": True, "record": record})
    return 0


def _wait_http(url: str, timeout: int = 90) -> None:
    deadline = time.monotonic() + timeout
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                if 200 <= response.status < 500:
                    return
        except Exception as exc:
            last_error = str(exc)
        time.sleep(2)
    raise TimeoutError(f"server not ready: {url}: {last_error}")


def _physical_check(run_root: Path, *, evidence_path: Path, execution_ids: list[str], page_id: str = "", extra: dict[str, Any] | None = None) -> dict[str, Any]:
    record = {
        "pass": True,
        "evidencePath": evidence_path.resolve().relative_to(run_root.resolve()).as_posix(),
        "evidenceSha256": sha256_file(evidence_path),
        "toolExecutionIds": execution_ids,
    }
    if page_id:
        record["pageId"] = page_id
    record.update(extra or {})
    return record


def _refresh_tool_evidence(run_root: Path, results: list[dict[str, Any]]) -> None:
    report_path = run_root / "test" / "test-report.json"
    report = read_json(report_path, {})
    by_tool: dict[str, dict[str, Any]] = {}
    for result in results:
        if not isinstance(result, dict) or result.get("exitCode") != 0:
            continue
        for tool_id in result.get("satisfiesToolIds", [result.get("toolId")]):
            if tool_id:
                by_tool[str(tool_id)] = result
    chromium = by_tool.get("web-playwright-chromium")
    if chromium:
        browser_result = run_root / "test" / "browser" / "chromium" / "result.json"
        if browser_result.is_file():
            data = read_json(browser_result, {})
            report["pageVisualChecks"] = []
            for page in data.get("pages", []):
                mobile = next((item for item in page.get("viewports", []) if item.get("id") == "mobile"), None)
                if mobile and Path(str(mobile.get("screenshot", ""))).is_file():
                    report["pageVisualChecks"].append(_physical_check(
                        run_root,
                        evidence_path=Path(mobile["screenshot"]),
                        execution_ids=[chromium["executionId"]],
                        page_id=str(page.get("pageId", "")),
                        extra={"browser": "chromium", "viewport": "mobile"},
                    ))
            common = _physical_check(run_root, evidence_path=browser_result, execution_ids=[chromium["executionId"]], extra={"browser": "chromium"})
            report["accessibilityChecks"] = [dict(common, checkId="axe-critical-serious")]
            report["responsiveChecks"] = [dict(common, checkId="mobile-tablet-desktop")]
            report["stateChecks"] = [dict(common, checkId="runtime-console-network-images-motion")]
    visual = by_tool.get("web-visual-regression")
    if visual:
        path = run_root / "test" / "visual-regression" / "result.json"
        if path.is_file():
            report["visualRegressionChecks"] = [_physical_check(run_root, evidence_path=path, execution_ids=[visual["executionId"]], extra={"checkId": "mockup-vs-runtime"})]
    lighthouse = by_tool.get("web-lighthouse")
    if lighthouse:
        path = run_root / "test" / "lighthouse" / "summary.json"
        if path.is_file():
            report["performanceChecks"] = [_physical_check(run_root, evidence_path=path, execution_ids=[lighthouse["executionId"]], extra={"checkId": "lighthouse-thresholds"})]
    security = by_tool.get("project-security-scan")
    if security:
        log = run_root / str(security.get("logPath", ""))
        if log.is_file():
            report["securityChecks"] = [_physical_check(run_root, evidence_path=log, execution_ids=[security["executionId"]], extra={"checkId": "secret-runtime-contamination"})]
    emulator_ids = ["android-emulator-boot", "android-emulator-health", "android-emulator-system-screenshot", "android-logcat-scan", "ios-simulator-boot", "ios-ui-test"]
    emulator_records = []
    for tool_id in emulator_ids:
        result = by_tool.get(tool_id)
        if not result:
            continue
        candidates = [
            run_root / "test" / "android-emulator" / "result.json",
            run_root / "test" / "ios-simulator" / "result.json",
        ]
        evidence = next((path for path in candidates if path.is_file()), None)
        if evidence:
            emulator_records.append(_physical_check(run_root, evidence_path=evidence, execution_ids=[result["executionId"]], extra={"toolId": tool_id, "apkInstallExcluded": True}))
    if emulator_records:
        unique = {}
        for item in emulator_records:
            unique[(item["evidencePath"], tuple(item["toolExecutionIds"]))] = item
        report["emulatorSimulatorChecks"] = list(unique.values())
    report["apkInstallationPolicy"] = "forbidden"
    write_json(report_path, report)


def cmd_run_toolchain(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    state = load_state(run_root)
    bootstrap = bootstrap_tooling(run_root, state)
    policy_path = run_root / "contract" / "tool-policy.json"
    policy = read_json(policy_path, {})
    config = policy.get("configuration", {})
    project = Path(str(state.get("projectRoot", "."))).resolve()
    target = str(state.get("targetPipeline", "web-responsive"))
    commands = suggested_commands(target, project, bootstrap["discovery"], config)
    selected = args.tool_id or required_tool_ids(run_root, target, project)
    results: list[dict[str, Any]] = []
    plugin_root = SCRIPT_ROOT.parent
    server = None
    server_log = None
    web_ids = {
        "web-playwright-chromium", "web-playwright-firefox", "web-playwright-webkit",
        "web-accessibility-axe", "web-responsive-matrix", "web-console-network",
        "web-visual-regression", "web-lighthouse",
    }
    try:
        if any(tool_id in web_ids for tool_id in selected):
            if not (plugin_root / "node_modules").is_dir():
                results.append(execute_tool(
                    run_root, state, tool_id="kh-aw-tooling-npm-install",
                    command="npm install", cwd=plugin_root, timeout=max(args.timeout, 1800),
                    artifacts=[str(plugin_root / "package-lock.json")],
                ))
                results.append(execute_tool(
                    run_root, state, tool_id="kh-aw-playwright-browser-install",
                    command="npx playwright install chromium firefox webkit", cwd=plugin_root, timeout=max(args.timeout, 1800),
                ))
            start_command = str(config.get("startCommand", "")).strip()
            base_url = str(config.get("baseUrl", "")).strip()
            ready_url = str(config.get("serverReadyUrl", base_url)).strip()
            if not start_command or not base_url:
                raise ValueError("web toolchain requires tool-policy.configuration.startCommand and baseUrl")
            if command_forbidden(start_command):
                raise ValueError("start command violates APK installation exclusion")
            server_log_path = run_root / "test" / "logs" / "web-server.log"
            server_log_path.parent.mkdir(parents=True, exist_ok=True)
            server_log = server_log_path.open("w", encoding="utf-8")
            popen_kwargs = {"shell": True, "cwd": project, "stdout": server_log, "stderr": subprocess.STDOUT, "text": True}
            if os.name == "nt":
                popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                popen_kwargs["start_new_session"] = True
            server = subprocess.Popen(start_command, **popen_kwargs)
            _wait_http(ready_url or base_url, timeout=120)

        processed: set[str] = set()
        for tool_id in selected:
            if tool_id in processed:
                continue
            if tool_id == "android-apk-install-excluded":
                marker = run_root / "test" / "logs" / "android-apk-install-excluded.log"
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text("APK installation is explicitly excluded. No adb install, installDebug, connectedAndroidTest, or bundletool install-apks command was executed.\n", encoding="utf-8")
                record = {
                    "executionId": f"POLICY-{len(read_json(run_root / 'test' / 'test-report.json', {}).get('toolExecutions', []))+1:04d}",
                    "toolId": tool_id, "satisfiesToolIds": [tool_id],
                    "command": "POLICY: APK_INSTALL_FORBIDDEN", "cwd": project.as_posix(),
                    "startedAt": utc_now(), "finishedAt": utc_now(), "durationMs": 0,
                    "exitCode": 0, "timedOut": False,
                    "logPath": marker.relative_to(run_root).as_posix(), "logSha256": sha256_file(marker),
                    "artifacts": [], "apkInstallExcluded": True, "status": "passed",
                }
                report = read_json(run_root / "test" / "test-report.json", {})
                report.setdefault("toolExecutions", []).append(record)
                report.setdefault("commands", []).append({"executionId": record["executionId"], "toolId": tool_id, "command": record["command"], "cwd": record["cwd"], "exitCode": 0, "outputPath": record["logPath"], "outputSha256": record["logSha256"], "recordedAt": utc_now()})
                write_json(run_root / "test" / "test-report.json", report)
                results.append(record); processed.add(tool_id); continue
            if tool_id == "project-security-scan":
                script = "from pathlib import Path; import json,sys; sys.path.insert(0," + repr(str(SCRIPT_ROOT)) + "); from kh_aw.security import scan_release_root; r=scan_release_root(Path('.').resolve()); print(json.dumps(r,ensure_ascii=False)); raise SystemExit(0 if r.get('status')=='passed' else 1)"
                results.append(execute_tool(run_root, state, tool_id=tool_id, command=f"python3 -c {json.dumps(script)}", cwd=project, timeout=300)); processed.add(tool_id); continue
            if tool_id in {"web-playwright-chromium", "web-accessibility-axe", "web-responsive-matrix", "web-console-network"}:
                base_url = str(config.get("baseUrl"))
                command = f"node {json.dumps(str(SCRIPT_ROOT / 'web_verify.mjs'))} --run-root {json.dumps(str(run_root))} --base-url {json.dumps(base_url)} --browser chromium"
                satisfies = ["web-playwright-chromium", "web-accessibility-axe", "web-responsive-matrix", "web-console-network"]
                results.append(execute_tool(run_root, state, tool_id="web-browser-suite-chromium", command=command, cwd=plugin_root, timeout=args.timeout, artifacts=[str(run_root / 'test' / 'browser' / 'chromium')], satisfies_tool_ids=satisfies)); processed.update(satisfies); continue
            if tool_id in {"web-playwright-firefox", "web-playwright-webkit"}:
                browser = "firefox" if tool_id.endswith("firefox") else "webkit"
                command = f"node {json.dumps(str(SCRIPT_ROOT / 'web_verify.mjs'))} --run-root {json.dumps(str(run_root))} --base-url {json.dumps(str(config.get('baseUrl')))} --browser {browser}"
                results.append(execute_tool(run_root, state, tool_id=tool_id, command=command, cwd=plugin_root, timeout=args.timeout, artifacts=[str(run_root / 'test' / 'browser' / browser)])); processed.add(tool_id); continue
            if tool_id == "web-visual-regression":
                command = f"node {json.dumps(str(SCRIPT_ROOT / 'visual_regression.mjs'))} --run-root {json.dumps(str(run_root))} --browser chromium"
                results.append(execute_tool(run_root, state, tool_id=tool_id, command=command, cwd=plugin_root, timeout=args.timeout, artifacts=[str(run_root / 'test' / 'visual-regression')])); processed.add(tool_id); continue
            if tool_id == "web-lighthouse":
                command = f"node {json.dumps(str(SCRIPT_ROOT / 'lighthouse_check.mjs'))} --run-root {json.dumps(str(run_root))} --url {json.dumps(str(config.get('baseUrl')))}"
                results.append(execute_tool(run_root, state, tool_id=tool_id, command=command, cwd=plugin_root, timeout=args.timeout, artifacts=[str(run_root / 'test' / 'lighthouse')])); processed.add(tool_id); continue
            android_suite_ids = {"android-emulator-list", "android-emulator-boot", "android-emulator-health", "android-emulator-system-screenshot", "android-logcat-scan"}
            if tool_id in android_suite_ids:
                avd = str(config.get("androidAvd", ""))
                serial = str(config.get("androidSerial", "") or "emulator-5554")
                command = f"python3 {json.dumps(str(SCRIPT_ROOT / 'android_emulator_suite.py'))} --run-root {json.dumps(str(run_root))} --serial {json.dumps(serial)}" + (f" --avd {json.dumps(avd)}" if avd else "")
                results.append(execute_tool(run_root, state, tool_id="android-emulator-suite", command=command, cwd=project, timeout=max(args.timeout, 300), artifacts=[str(run_root / 'test' / 'android-emulator')], satisfies_tool_ids=sorted(android_suite_ids))); processed.update(android_suite_ids); continue
            ios_suite_ids = {"ios-simulator-list", "ios-simulator-boot", "ios-ui-test"}
            if tool_id in ios_suite_ids:
                device = str(config.get("iosDevice", ""))
                command = f"python3 {json.dumps(str(SCRIPT_ROOT / 'ios_simulator_suite.py'))} --run-root {json.dumps(str(run_root))}" + (f" --device {json.dumps(device)}" if device else "")
                results.append(execute_tool(run_root, state, tool_id="ios-simulator-suite", command=command, cwd=project, timeout=max(args.timeout, 300), artifacts=[str(run_root / 'test' / 'ios-simulator')], satisfies_tool_ids=sorted(ios_suite_ids))); processed.update(ios_suite_ids); continue
            command = commands.get(tool_id)
            if not command:
                results.append({"toolId": tool_id, "status": "configuration-required", "exitCode": 2})
                processed.add(tool_id); continue
            try:
                artifact_globs: list[str] = []
                if tool_id == "web-build":
                    artifact_globs = ["dist", "build", "out", ".next"]
                elif tool_id in {"android-gradle-build", "flutter-build-apk"}:
                    artifact_globs = ["**/build/outputs/apk/**/*.apk", "**/build/app/outputs/flutter-apk/*.apk"]
                elif tool_id == "ios-build":
                    artifact_globs = ["**/build/**/*.app", "**/DerivedData/**/Build/Products/**/*.app"]
                results.append(execute_tool(
                    run_root,
                    state,
                    tool_id=tool_id,
                    command=command,
                    cwd=project,
                    timeout=args.timeout,
                    artifact_globs=artifact_globs,
                ))
            except Exception as exc:
                results.append({"toolId": tool_id, "status": "blocked", "exitCode": 2, "error": str(exc)})
            processed.add(tool_id)
    finally:
        if server is not None:
            try:
                if os.name == "nt":
                    server.send_signal(signal.CTRL_BREAK_EVENT)
                else:
                    os.killpg(server.pid, signal.SIGTERM)
                server.wait(timeout=10)
            except Exception:
                try:
                    if os.name == "nt":
                        server.kill()
                    else:
                        os.killpg(server.pid, signal.SIGKILL)
                except Exception:
                    server.kill()
        if server_log is not None:
            server_log.close()
    report_path = run_root / "test" / "test-report.json"
    report = read_json(report_path, {})
    report["toolDiscovery"] = {"path": bootstrap["discovery"]["path"], "sha256": bootstrap["discovery"]["sha256"]}
    report["apkInstallationPolicy"] = "forbidden"
    write_json(report_path, report)
    _refresh_tool_evidence(run_root, results)
    emit({"ok": all(item.get("exitCode") == 0 for item in results), "results": results})
    return 0 if all(item.get("exitCode") == 0 for item in results) else 1


def cmd_scan_security(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    state = load_state(run_root)
    root = safe_resolve(args.root, Path(str(state.get("projectRoot", ".")))) if args.root else Path(str(state.get("projectRoot", ".")))
    result = scan_release_root(root)
    release_path = run_root / "release" / "release.json"
    release = read_json(release_path, {})
    release["securityScan"] = result
    write_json(release_path, release)
    emit(result)
    return 0 if result["status"] == "passed" else 1


def cmd_audit_session(args: argparse.Namespace) -> int:
    run_root = resolve_run(args)
    result = build_session_forensics(
        run_root,
        safe_resolve(args.session_jsonl),
        args.session_id,
    )
    emit({"ok": result.get("completionTruth") == "verified", "sessionForensics": result})
    return 0 if result.get("completionTruth") == "verified" else 1


def cmd_build_package_manifest(args: argparse.Namespace) -> int:
    plugin_root = safe_resolve(args.plugin_root or SCRIPT_ROOT.parent)
    manifest = build_package_manifest(plugin_root)
    emit({"ok": True, "manifest": manifest, "path": (plugin_root / "PACKAGE_MANIFEST.json").as_posix()})
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    plugin_root = safe_resolve(args.plugin_root or SCRIPT_ROOT.parent)
    marketplace_root = safe_resolve(args.marketplace_root) if args.marketplace_root else None
    result = run_doctor(
        plugin_root,
        marketplace_root,
        include_distribution=bool(args.distribution),
        codex_home=safe_resolve(args.codex_home) if args.codex_home else None,
    )
    emit(result)
    return 0 if result["ok"] else 1


def cmd_resume(args: argparse.Namespace) -> int:
    result = resume_run(resolve_run(args))
    emit(result)
    return 0


def cmd_installation_status(args: argparse.Namespace) -> int:
    home = safe_resolve(args.codex_home) if args.codex_home else None
    result = resolve_active_installation(args.plugin_name, home, args.version)
    emit({"ok": result.get("active") is not None, **result})
    return 0 if result.get("active") is not None else 1


def cmd_build_package(args: argparse.Namespace) -> int:
    plugin_root = safe_resolve(args.plugin_root or SCRIPT_ROOT.parent)
    marketplace_root = plugin_root.parents[1]
    ledger = version_ledger(marketplace_root)
    if not ledger["consistent"]:
        emit({"ok": False, "error": "version ledger is inconsistent", "versionLedger": ledger})
        return 1
    build_package_manifest(plugin_root)
    output = safe_resolve(args.output or marketplace_root / "dist" / f"kh-aw-{ledger['version']}.zip")
    first = build_deterministic_zip(plugin_root, output)
    check = build_deterministic_zip(plugin_root, output.with_suffix(".verify.zip"))
    reproducible = first["sha256"] == check["sha256"]
    if check["path"] != first["path"]:
        Path(check["path"]).unlink(missing_ok=True)
    emit({"ok": reproducible, "package": first, "reproducible": reproducible, "versionLedger": ledger})
    return 0 if reproducible else 1


def cmd_build_release_manifest(args: argparse.Namespace) -> int:
    root = safe_resolve(args.marketplace_root or SCRIPT_ROOT.parents[1])
    manifest = build_release_manifest(root)
    write_json(root / "RELEASE_MANIFEST.json", manifest)
    emit({"ok": True, "path": (root / "RELEASE_MANIFEST.json").as_posix(), "manifest": manifest})
    return 0


def cmd_e2e(args: argparse.Namespace) -> int:
    result = run_local_e2e(safe_resolve(args.plugin_root or SCRIPT_ROOT.parent))
    emit(result)
    return 0 if result["pass"] else 1


def cmd_project_doctor(args: argparse.Namespace) -> int:
    result = run_project_doctor(resolve_run(args))
    emit(result)
    return 0 if result["ok"] else 1


def cmd_verify_run(args: argparse.Namespace) -> int:
    result = verify_run(resolve_run(args))
    emit(result)
    return 0 if result["pass"] else 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kh_aw", description="KH_Aw evidence-gated Codex app/web company workflow")
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Initialize a protected KH_Aw run")
    init.add_argument("--project-root", default=".")
    init.add_argument("--analysis-folder")
    init.add_argument("--output-root")
    init.add_argument("--instructions-file", required=True)
    init.add_argument("--target", choices=["web-responsive", "app-mobile-webview", "android-native", "ios-native", "cross-platform", "codex-plugin", "unknown-needs-confirmation"], default="unknown-needs-confirmation")
    init.add_argument("--target-auto", action="store_true", help="Infer and lock the target pipeline from instructions and project files")
    init.add_argument("--name")
    init.set_defaults(func=cmd_init)
    for name, func in [("status", cmd_status), ("gate", cmd_gate), ("advance", cmd_advance), ("finalize", cmd_finalize)]:
        cmd = sub.add_parser(name)
        cmd.add_argument("--run-root")
        cmd.add_argument("--project-root", default=".")
        cmd.add_argument("--workspace-root")
        if name in {"gate", "advance"}:
            cmd.add_argument("--stage", choices=STAGES, required=name == "gate")
        if name == "gate":
            cmd.add_argument("--ignore-order", action="store_true")
        if name in {"gate", "advance", "finalize"}:
            cmd.add_argument("--strict", action="store_true")
        cmd.set_defaults(func=func)
    prepare_agents = sub.add_parser("prepare-agents", help="Compute and lock a dynamic 2-60 subagent plan for one stage")
    prepare_agents.add_argument("--run-root", required=True)
    prepare_agents.add_argument("--stage", choices=STAGES, required=True)
    prepare_agents.add_argument("--count", type=int)
    prepare_agents.add_argument("--justification-file")
    prepare_agents.add_argument("--force", action="store_true")
    prepare_agents.set_defaults(func=cmd_prepare_agents)
    record_agent = sub.add_parser("record-subagent", help="Register one independently executed Codex subagent result with physical evidence")
    record_agent.add_argument("--run-root", required=True)
    record_agent.add_argument("--stage", choices=STAGES, required=True)
    record_agent.add_argument("--worker-id", required=True)
    record_agent.add_argument("--task-id")
    record_agent.add_argument("--session-id", required=True)
    record_agent.add_argument("--invocation", required=True)
    record_agent.add_argument(
        "--delegation-mode",
        choices=["native-agents", "codex-subagent", "independent-task"],
        default="codex-subagent",
    )
    record_agent.add_argument("--invocation-receipt-file", required=True)
    record_agent.add_argument("--session-evidence-file", required=True)
    record_agent.add_argument("--evidence-file", required=True)
    record_agent.add_argument("--review-of", action="append")
    record_agent.set_defaults(func=cmd_record_subagent)
    aggregate_agents = sub.add_parser("aggregate-agents", help="Register the stage lead AI aggregation of all subagent outputs")
    aggregate_agents.add_argument("--run-root", required=True)
    aggregate_agents.add_argument("--stage", choices=STAGES, required=True)
    aggregate_agents.add_argument("--lead-agent-id", required=True)
    aggregate_agents.add_argument("--lead-session-id", required=True)
    aggregate_agents.add_argument("--session-evidence-file", required=True)
    aggregate_agents.add_argument("--evidence-file", required=True)
    aggregate_agents.add_argument("--accepted-worker-id", action="append")
    aggregate_agents.add_argument("--resolved-conflict", action="append")
    aggregate_agents.set_defaults(func=cmd_aggregate_agents)
    agent_status = sub.add_parser("agent-status", help="Validate stage subagent count, independent sessions, evidence, cross-review, and lead aggregation")
    agent_status.add_argument("--run-root", required=True)
    agent_status.add_argument("--stage", choices=STAGES, required=True)
    agent_status.set_defaults(func=cmd_agent_status)
    reg = sub.add_parser("register-source", help="Register a body file fetched by Codex web tools")
    reg.add_argument("--run-root", required=True)
    reg.add_argument("--element-id", required=True)
    reg.add_argument("--source-type", choices=["web", "github", "official"], required=True)
    reg.add_argument("--url", required=True)
    reg.add_argument("--body-file", required=True)
    reg.add_argument("--title")
    reg.add_argument("--query")
    reg.add_argument("--http-status", type=int, default=200)
    reg.add_argument("--project-fit-reason", required=True)
    reg.add_argument("--license-note")
    reg.add_argument("--session-id", required=True)
    reg.add_argument("--retrieval-evidence-file", required=True)
    reg.set_defaults(func=cmd_register_source)
    fetch = sub.add_parser("fetch-source", help="Fetch and register an actual page body")
    fetch.add_argument("--run-root", required=True)
    fetch.add_argument("--element-id", required=True)
    fetch.add_argument("--source-type", choices=["web", "github", "official"], required=True)
    fetch.add_argument("--url", required=True)
    fetch.add_argument("--query")
    fetch.add_argument("--project-fit-reason", required=True)
    fetch.add_argument("--license-note")
    fetch.add_argument("--timeout", type=int, default=30)
    fetch.set_defaults(func=cmd_fetch_source)
    record = sub.add_parser("record-command", help="Execute and record a physical build/test command")
    record.add_argument("--run-root", required=True)
    record.add_argument("--tool-id", default="custom-command")
    record.add_argument("--command", required=True)
    record.add_argument("--cwd")
    record.add_argument("--timeout", type=int, default=1800)
    record.add_argument("--artifact", action="append")
    record.add_argument("--strict", action="store_true")
    record.set_defaults(func=cmd_record_command)
    bootstrap = sub.add_parser("bootstrap-tools", help="Discover real tools and create target-specific tool policy")
    bootstrap.add_argument("--run-root", required=True)
    bootstrap.set_defaults(func=cmd_bootstrap_tools)
    configure = sub.add_parser("configure-tools", help="Configure real project URLs, servers, emulator/simulator IDs, and target commands")
    configure.add_argument("--run-root", required=True)
    configure.add_argument("--base-url")
    configure.add_argument("--start-command")
    configure.add_argument("--server-ready-url")
    configure.add_argument("--android-avd")
    configure.add_argument("--android-serial")
    configure.add_argument("--ios-device")
    configure.add_argument("--command", action="append", help="TOOL_ID=COMMAND; APK installation commands are rejected")
    configure.set_defaults(func=cmd_configure_tools)
    native = sub.add_parser("record-native", help="Record physical evidence from an available Codex native/slash capability")
    native.add_argument("--run-root", required=True)
    native.add_argument("--capability-id", required=True)
    native.add_argument("--evidence-file", required=True)
    native.add_argument("--invocation", required=True)
    native.add_argument("--tool-execution-id", action="append")
    native.add_argument("--session-id", required=True)
    native.add_argument("--session-evidence-file", required=True)
    native.set_defaults(func=cmd_record_native)
    native_fallback = sub.add_parser("exercise-native", help="Execute a physical fallback for a Codex native/slash capability")
    native_fallback.add_argument("--run-root", required=True)
    native_fallback.add_argument("--capability-id", required=True)
    native_fallback.set_defaults(func=cmd_exercise_native)
    toolchain = sub.add_parser("run-toolchain", help="Run target-specific build, browser, emulator, simulator, QA tools; APK install is forbidden")
    toolchain.add_argument("--run-root", required=True)
    toolchain.add_argument("--tool-id", action="append")
    toolchain.add_argument("--timeout", type=int, default=1800)
    toolchain.add_argument("--strict", action="store_true")
    toolchain.set_defaults(func=cmd_run_toolchain)
    scan = sub.add_parser("scan-security", help="Scan release root for secrets and runtime/browser contamination")
    scan.add_argument("--run-root", required=True)
    scan.add_argument("--root")
    scan.add_argument("--strict", action="store_true")
    scan.set_defaults(func=cmd_scan_security)
    audit_session = sub.add_parser("audit-session", help="Parse and bind the physical Codex session JSONL to completion evidence")
    audit_session.add_argument("--run-root", required=True)
    audit_session.add_argument("--session-jsonl", required=True)
    audit_session.add_argument("--session-id", required=True)
    audit_session.set_defaults(func=cmd_audit_session)
    integrity = sub.add_parser("build-package-manifest", help="Generate the physical package SHA-256 manifest")
    integrity.add_argument("--plugin-root")
    integrity.set_defaults(func=cmd_build_package_manifest)
    doctor = sub.add_parser("doctor", help="Validate plugin and marketplace package")
    doctor.add_argument("--plugin-root")
    doctor.add_argument("--marketplace-root")
    doctor.add_argument("--distribution", action="store_true")
    doctor.add_argument("--codex-home")
    doctor.set_defaults(func=cmd_doctor)
    resume = sub.add_parser("resume", help="Resume the earliest incomplete stage without losing repair history")
    resume.add_argument("--run-root")
    resume.add_argument("--project-root", default=".")
    resume.add_argument("--workspace-root")
    resume.set_defaults(func=cmd_resume)
    installation = sub.add_parser("installation-status", help="Inspect Codex cache versions, duplicates, and active resolution")
    installation.add_argument("--plugin-name", default="kh-aw")
    installation.add_argument("--version", default="")
    installation.add_argument("--codex-home")
    installation.set_defaults(func=cmd_installation_status)
    package = sub.add_parser("build-package", help="Build and verify a deterministic versioned plugin ZIP")
    package.add_argument("--plugin-root")
    package.add_argument("--output")
    package.set_defaults(func=cmd_build_package)
    release_manifest = sub.add_parser("build-release-manifest", help="Regenerate the marketplace-wide release ledger")
    release_manifest.add_argument("--marketplace-root")
    release_manifest.set_defaults(func=cmd_build_release_manifest)
    e2e = sub.add_parser("e2e", help="Run cache, CRLF, shadowing, and reproducible package scenarios")
    e2e.add_argument("--plugin-root")
    e2e.set_defaults(func=cmd_e2e)
    for name, func, help_text in [
        ("project-doctor", cmd_project_doctor, "Validate project state, runtime, graph, and reachability"),
        ("verify-run", cmd_verify_run, "Independently verify all gates, requirements, and release receipt"),
    ]:
        command = sub.add_parser(name, help=help_text)
        command.add_argument("--run-root")
        command.add_argument("--project-root", default=".")
        command.add_argument("--workspace-root")
        command.set_defaults(func=func)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except Exception as exc:
        emit({"ok": False, "status": "tool-error", "errorType": type(exc).__name__, "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
