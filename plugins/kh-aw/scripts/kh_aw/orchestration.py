from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path
from typing import Any

STAGES = ["intake", "analyze", "research", "design", "implement", "review", "test", "release"]
from .tooling import canonical_required_tool_ids
from .util import read_json, sha256_file, slug, utc_now, write_json

MIN_SUBAGENTS = 2
MAX_SUBAGENTS = 60

STAGE_ROLE_POOLS: dict[str, list[str]] = {
    "intake": [
        "requirement-preserver", "constraint-auditor", "analysis-mode-verifier",
        "path-safety-verifier", "policy-lock-reviewer", "acceptance-criteria-reviewer",
    ],
    "analyze": [
        "inventory-auditor", "architecture-analyst", "requirements-tracer", "page-flow-analyst",
        "data-model-analyst", "logic-flow-analyst", "security-analyst", "performance-analyst",
        "dependency-analyst", "platform-analyst", "accessibility-analyst", "analysis-cross-reviewer",
    ],
    "research": [
        "competitor-researcher", "feature-researcher", "design-system-researcher",
        "image-researcher", "font-researcher", "icon-researcher", "motion-researcher",
        "accessibility-researcher", "platform-researcher", "conversion-researcher",
        "source-body-verifier", "license-provenance-reviewer", "research-cross-reviewer",
    ],
    "design": [
        "information-architect", "interaction-designer", "visual-art-director", "page-mockup-designer",
        "image-system-designer", "motion-system-designer", "responsive-designer",
        "accessibility-designer", "conversion-designer", "design-consistency-reviewer",
        "small-business-attention-reviewer", "design-cross-reviewer",
    ],
    "implement": [
        "frontend-implementer", "backend-implementer", "data-implementer", "integration-implementer",
        "motion-implementer", "image-asset-implementer", "accessibility-implementer",
        "performance-implementer", "security-implementer", "platform-implementer",
        "implementation-reviewer", "implementation-cross-reviewer",
    ],
    "review": [
        "visual-reviewer", "interaction-reviewer", "requirements-reviewer", "responsive-reviewer",
        "accessibility-reviewer", "motion-reviewer", "image-quality-reviewer", "state-reviewer",
        "security-reviewer", "performance-reviewer", "cross-page-reviewer", "review-cross-reviewer",
    ],
    "test": [
        "build-verifier", "unit-test-verifier", "lint-verifier", "browser-e2e-verifier",
        "accessibility-tool-verifier", "performance-tool-verifier", "visual-regression-verifier",
        "emulator-simulator-verifier", "runtime-log-verifier", "security-scan-verifier",
        "apk-policy-verifier", "test-cross-reviewer",
    ],
    "release": [
        "artifact-verifier", "security-release-verifier", "installation-doc-reviewer",
        "rollback-reviewer", "privacy-reviewer", "cost-reviewer", "marketplace-reviewer",
        "github-release-reviewer", "release-notes-reviewer", "release-cross-reviewer",
    ],
}


def orchestration_policy() -> dict[str, Any]:
    return {
        "schemaVersion": "3.2",
        "generatedAt": utc_now(),
        "mode": "dynamic-multi-agent-every-stage",
        "minimumSubAgentsPerStage": MIN_SUBAGENTS,
        "maximumSubAgentsPerStage": MAX_SUBAGENTS,
        "fixedSixtyForbidden": True,
        "promptOnlyDelegationForbidden": True,
        "independentAgentSessionRequired": True,
        "physicalOutputEvidenceRequired": True,
        "uniqueSessionPerWorkerRequired": True,
        "crossReviewRequired": True,
        "fullRingCrossReviewRequired": True,
        "immutableDispatchContractRequired": True,
        "invocationReceiptRequired": True,
        "leadContractRequired": True,
        "leadAggregationRequired": True,
        "leadScaleJustificationRequired": True,
        "everyStageRequired": list(STAGES),
        "scalingSignals": [
            "inventory.fileCount", "inventory.directoryCount", "inventory.totalBytes",
            "requirements.count", "pages.count", "fields.count", "logic.count",
            "features.count", "risks.count", "researchElements.count", "requiredTools.count",
            "releaseArtifacts.count",
        ],
        "rule": (
            'Each stage lead dynamically assigns 2 to 60 independent Codex workers based on project scale. Fixed 60-worker fan-out is forbidden. Physical sessions, unique outputs, SHA-256 evidence, cross-review, and lead aggregation are mandatory.'
        ),
    }


def _count(payload: Any, key: str | None = None) -> int:
    if key is not None and isinstance(payload, dict):
        payload = payload.get(key, [])
    return len(payload) if isinstance(payload, list) else 0


def _signals(run_root: Path, state: dict[str, Any], stage: str) -> dict[str, int]:
    inventory = read_json(run_root / "inventory" / "inventory-summary.json", {})
    requirements = read_json(run_root / "contract" / "requirements.json", {})
    analysis = read_json(run_root / "analysis" / "analysis-ledger.json", {})
    pages_payload = read_json(run_root / "design" / "page-inventory.json", {})
    research = read_json(run_root / "evidence" / "research-plan.json", {})
    release = read_json(run_root / "release" / "release.json", {})
    project_root = Path(str(state.get("projectRoot", "."))).resolve()
    target = str(state.get("targetPipeline", "web-responsive"))
    return {
        "fileCount": int(inventory.get("fileCount", 0) or 0),
        "directoryCount": int(inventory.get("directoryCount", 0) or 0),
        "totalBytes": int(inventory.get("totalBytes", 0) or 0),
        "requirementCount": _count(requirements, "requirements"),
        "pageCount": _count(pages_payload, "pages") or _count(analysis, "pageInventory"),
        "fieldCount": _count(analysis, "fieldInventory"),
        "logicCount": _count(analysis, "logicInventory"),
        "featureCount": _count(analysis, "featureInventory"),
        "riskCount": _count(analysis, "risks") + _count(analysis, "securityFindings") + _count(analysis, "performanceFindings"),
        "researchElementCount": _count(research, "elements"),
        "requiredToolCount": len(canonical_required_tool_ids(target, project_root)),
        "releaseArtifactCount": _count(release, "artifacts"),
    }


def recommended_subagent_count(run_root: Path, state: dict[str, Any], stage: str) -> tuple[int, dict[str, int], list[str]]:
    if stage not in STAGES:
        raise ValueError(f"unknown stage: {stage}")
    s = _signals(run_root, state, stage)
    reasons: list[str] = []
    count = MIN_SUBAGENTS

    if stage == "intake":
        count += math.ceil(max(0, s["requirementCount"] - 20) / 20)
        reasons.append(f"requirements={s['requirementCount']}")
    elif stage == "analyze":
        count += math.ceil(max(0, s["fileCount"] - 50) / 250)
        count += math.ceil(max(0, s["directoryCount"] - 20) / 100)
        count += math.ceil(max(0, s["requirementCount"] - 20) / 20)
        count += math.ceil(s["riskCount"] / 10)
        reasons.extend([f"files={s['fileCount']}", f"dirs={s['directoryCount']}", f"requirements={s['requirementCount']}", f"risks={s['riskCount']}"])
    elif stage == "research":
        count += math.ceil(max(0, s["researchElementCount"] - 4) / 3)
        count += math.ceil(max(0, s["pageCount"] - 5) / 5)
        count += math.ceil(max(0, s["requirementCount"] - 25) / 25)
        reasons.extend([f"researchElements={s['researchElementCount']}", f"pages={s['pageCount']}", f"requirements={s['requirementCount']}"])
    elif stage == "design":
        count += math.ceil(max(0, s["pageCount"] - 2) / 2)
        count += math.ceil(max(0, s["fieldCount"] - 40) / 40)
        count += math.ceil(max(0, s["featureCount"] - 20) / 20)
        reasons.extend([f"pages={s['pageCount']}", f"fields={s['fieldCount']}", f"features={s['featureCount']}"])
    elif stage == "implement":
        count += math.ceil(max(0, s["pageCount"] - 2) / 2)
        count += math.ceil(max(0, s["featureCount"] - 15) / 15)
        count += math.ceil(max(0, s["logicCount"] - 20) / 20)
        count += math.ceil(max(0, s["fileCount"] - 250) / 500)
        reasons.extend([f"pages={s['pageCount']}", f"features={s['featureCount']}", f"logic={s['logicCount']}", f"files={s['fileCount']}"])
    elif stage == "review":
        count += math.ceil(max(0, s["pageCount"] - 3) / 3)
        count += math.ceil(max(0, s["featureCount"] - 30) / 30)
        count += math.ceil(max(0, s["riskCount"] - 5) / 10)
        reasons.extend([f"pages={s['pageCount']}", f"features={s['featureCount']}", f"risks={s['riskCount']}"])
    elif stage == "test":
        count += math.ceil(max(0, s["requiredToolCount"] - 4) / 2)
        count += math.ceil(max(0, s["pageCount"] - 5) / 5)
        count += math.ceil(max(0, s["riskCount"] - 5) / 10)
        reasons.extend([f"requiredTools={s['requiredToolCount']}", f"pages={s['pageCount']}", f"risks={s['riskCount']}"])
    elif stage == "release":
        count += math.ceil(max(0, s["releaseArtifactCount"] - 3) / 3)
        count += math.ceil(max(0, s["requiredToolCount"] - 8) / 8)
        count += math.ceil(max(0, s["requirementCount"] - 40) / 40)
        reasons.extend([f"artifacts={s['releaseArtifactCount']}", f"requiredTools={s['requiredToolCount']}", f"requirements={s['requirementCount']}"])

    count = max(MIN_SUBAGENTS, min(MAX_SUBAGENTS, count))
    return count, s, reasons


def _scope_units(run_root: Path, stage: str) -> list[str]:
    requirements = read_json(run_root / "contract" / "requirements.json", {})
    analysis = read_json(run_root / "analysis" / "analysis-ledger.json", {})
    pages = read_json(run_root / "design" / "page-inventory.json", {})
    research = read_json(run_root / "evidence" / "research-plan.json", {})
    if stage == "intake":
        values = [str(item.get("id")) for item in requirements.get("requirements", []) if isinstance(item, dict) and item.get("id")]
    elif stage == "analyze":
        values = ["full-file-inventory", "architecture", "requirements", "security", "performance", "pages", "data", "logic"]
        inventory_path = run_root / "inventory" / "inventory.jsonl"
        if inventory_path.is_file():
            import json
            try:
                with inventory_path.open("r", encoding="utf-8", errors="replace") as stream:
                    for line in stream:
                        if len(values) >= 508:
                            break
                        try:
                            item = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(item, dict) and item.get("path"):
                            values.append(str(item["path"]))
            except OSError:
                pass
    elif stage == "research":
        values = [str(item.get("id")) for item in research.get("elements", []) if isinstance(item, dict) and item.get("id")]
    elif stage in {"design", "implement", "review", "test"}:
        values = [str(item.get("pageId")) for item in pages.get("pages", []) if isinstance(item, dict) and item.get("pageId")]
        if not values:
            values = [str(item.get("pageId")) for item in analysis.get("pageInventory", []) if isinstance(item, dict) and item.get("pageId")]
    else:
        values = ["artifacts", "installation", "rollback", "privacy", "security", "marketplace", "release-notes"]
    return values or [f"{stage}-complete-scope"]


def _json_fingerprint(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _resolve_scale_justification(
    run_root: Path,
    *,
    safety_floor: int,
    selected_count: int,
    justification_file: Path | None,
) -> dict[str, Any]:
    if selected_count <= safety_floor:
        return {"path": "", "sha256": "", "bytes": 0}
    if justification_file is None:
        raise ValueError("increasing the subagent count above the safety floor requires a physical justification file")
    candidate = justification_file.expanduser().resolve()
    try:
        rel = candidate.relative_to(run_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("subagent scale justification must stay inside run root") from exc
    if not candidate.is_file() or candidate.stat().st_size < 120:
        raise ValueError("subagent scale justification must be a physical file of at least 120 bytes")
    if not candidate.read_text(encoding="utf-8", errors="replace").strip():
        raise ValueError("subagent scale justification cannot be empty")
    return {"path": rel, "sha256": sha256_file(candidate), "bytes": candidate.stat().st_size}


def canonical_agent_plan(
    run_root: Path,
    state: dict[str, Any],
    stage: str,
    *,
    selected_count: int | None = None,
    justification_file: Path | None = None,
) -> dict[str, Any]:
    safety_floor, signals, reasons = recommended_subagent_count(run_root, state, stage)
    count = safety_floor if selected_count is None else int(selected_count)
    if count < MIN_SUBAGENTS or count > MAX_SUBAGENTS:
        raise ValueError("subagent count must stay between 2 and 60")
    if count < safety_floor:
        raise ValueError(f"subagent count {count} is below the calculated safety floor {safety_floor}")
    justification = _resolve_scale_justification(
        run_root,
        safety_floor=safety_floor,
        selected_count=count,
        justification_file=justification_file,
    )
    roles = STAGE_ROLE_POOLS[stage]
    scopes = _scope_units(run_root, stage)
    worker_ids = [f"{stage.upper()}-AGENT-{index + 1:02d}" for index in range(count)]
    assignments: list[dict[str, Any]] = []
    for index, worker_id in enumerate(worker_ids):
        role = roles[index % len(roles)]
        assigned = [scope for offset, scope in enumerate(scopes) if offset % count == index]
        if not assigned:
            assigned = [scopes[index % len(scopes)]]
        assignments.append({
            "workerId": worker_id,
            "taskId": f"{stage.upper()}-TASK-{index + 1:02d}",
            "role": role,
            "scopeIds": assigned,
            "reviewTargetWorkerIds": [worker_ids[(index + 1) % count]],
            "independentSessionRequired": True,
            "physicalOutputRequired": True,
            "immutableDispatchContractRequired": True,
            "invocationReceiptRequired": True,
            "crossReviewRequired": True,
            "status": "planned",
        })
    fingerprint_payload = {
        "schemaVersion": "3.2",
        "stage": stage,
        "safetyFloor": safety_floor,
        "selectedSubAgents": count,
        "signals": signals,
        "scaleJustificationSha256": justification["sha256"],
        "assignments": [
            {
                "workerId": item["workerId"],
                "taskId": item["taskId"],
                "role": item["role"],
                "scopeIds": item["scopeIds"],
                "reviewTargetWorkerIds": item["reviewTargetWorkerIds"],
            }
            for item in assignments
        ],
    }
    return {
        "schemaVersion": "3.2",
        "generatedAt": utc_now(),
        "stage": stage,
        "leadAgent": {
            "agentId": f"{stage.upper()}-LEAD",
            "role": f"{stage}-lead-agent",
            "responsibility": 'Assign workers, remove duplication, resolve conflicts, verify omissions, and aggregate final stage evidence.',
        },
        "minimumSubAgents": MIN_SUBAGENTS,
        "maximumSubAgents": MAX_SUBAGENTS,
        "safetyFloorSubAgents": safety_floor,
        "recommendedSubAgents": count,
        "selectedSubAgents": count,
        "fixedSixty": False,
        "dynamicScaling": True,
        "leadScaleOverride": count > safety_floor,
        "scaleJustification": justification,
        "scalingSignals": signals,
        "scalingReasons": reasons,
        "assignments": assignments,
        "planFingerprint": _json_fingerprint(fingerprint_payload),
    }


def _dispatch_payload(stage: str, plan: dict[str, Any], assignment: dict[str, Any]) -> dict[str, Any]:
    return {
        "schemaVersion": "3.2",
        "stage": stage,
        "planFingerprint": plan["planFingerprint"],
        "workerId": assignment["workerId"],
        "taskId": assignment["taskId"],
        "role": assignment["role"],
        "scopeIds": assignment["scopeIds"],
        "reviewTargetWorkerIds": assignment["reviewTargetWorkerIds"],
        "independentSessionRequired": True,
        "physicalOutputRequired": True,
        "invocationReceiptRequired": True,
        "rule": "Use a real independent Codex session and return physical evidence containing every immutable identity marker.",
    }


def ensure_agent_plan(
    run_root: Path,
    state: dict[str, Any],
    stage: str,
    *,
    force: bool = False,
    selected_count: int | None = None,
    justification_file: Path | None = None,
) -> dict[str, Any]:
    root = run_root / "orchestration" / stage
    root.mkdir(parents=True, exist_ok=True)
    path = root / "agent-plan.json"
    existing = read_json(path, None)
    if existing is not None and not force:
        if selected_count is not None or justification_file is not None:
            raise ValueError("use force=True when replacing an existing agent plan")
        return existing
    if force:
        for stale in [
            root / "lead-aggregation.json", root / "execution-ledger.json",
            root / "dispatch-manifest.json", root / "lead-contract.json", path,
        ]:
            if stale.is_file():
                stale.unlink()
        for folder in ["results", "dispatch", "receipts"]:
            target = root / folder
            if target.is_dir():
                shutil.rmtree(target)
    for folder in ["results", "dispatch", "receipts", "outputs"]:
        (root / folder).mkdir(parents=True, exist_ok=True)
    plan = canonical_agent_plan(
        run_root,
        state,
        stage,
        selected_count=selected_count,
        justification_file=justification_file,
    )
    dispatch_records: list[dict[str, Any]] = []
    for assignment in plan["assignments"]:
        dispatch_path = root / "dispatch" / f"{slug(assignment['workerId'])}.json"
        write_json(dispatch_path, _dispatch_payload(stage, plan, assignment))
        dispatch_rel = dispatch_path.relative_to(run_root).as_posix()
        dispatch_sha = sha256_file(dispatch_path)
        assignment["dispatchContractPath"] = dispatch_rel
        assignment["dispatchContractSha256"] = dispatch_sha
        dispatch_records.append({
            "workerId": assignment["workerId"],
            "path": dispatch_rel,
            "sha256": dispatch_sha,
            "bytes": dispatch_path.stat().st_size,
        })
    write_json(path, plan)
    plan_sha = sha256_file(path)
    lead_contract = {
        "schemaVersion": "3.2",
        "stage": stage,
        "leadAgentId": plan["leadAgent"]["agentId"],
        "planFingerprint": plan["planFingerprint"],
        "agentPlanPath": path.relative_to(run_root).as_posix(),
        "agentPlanSha256": plan_sha,
        "requiredWorkerIds": [item["workerId"] for item in plan["assignments"]],
        "requiredDispatchContractSha256": [item["dispatchContractSha256"] for item in plan["assignments"]],
        "requireAllWorkersAccepted": True,
        "requireConflictAndCoverageResolution": True,
    }
    lead_contract_path = root / "lead-contract.json"
    write_json(lead_contract_path, lead_contract)
    lead_contract_sha = sha256_file(lead_contract_path)
    write_json(root / "execution-ledger.json", {
        "schemaVersion": "3.2", "stage": stage, "updatedAt": utc_now(), "workers": [],
    })
    write_json(root / "dispatch-manifest.json", {
        "schemaVersion": "3.2",
        "stage": stage,
        "dispatchMode": "Codex-native-agents-or-independent-Codex-tasks",
        "preferredInvocation": "/agents",
        "workerCount": plan["selectedSubAgents"],
        "planFingerprint": plan["planFingerprint"],
        "dispatchContracts": dispatch_records,
        "leadContractPath": lead_contract_path.relative_to(run_root).as_posix(),
        "leadContractSha256": lead_contract_sha,
        "rule": "Each assignment requires a real independent Codex session, immutable dispatch contract, invocation receipt, unique output, ring cross-review, and lead aggregation.",
    })
    return plan


def _validate_codex_session_evidence(
    session_evidence_file: Path,
    *,
    session_id: str,
    task_id: str,
) -> tuple[str, str, int]:
    path = session_evidence_file.expanduser().resolve()
    normalized = path.as_posix().lower()
    if "/.codex/sessions/" not in normalized or not path.name.lower().startswith("rollout-") or path.suffix.lower() != ".jsonl":
        raise ValueError("subagent session evidence must be a physical Codex rollout JSONL under .codex/sessions")
    if not path.is_file() or path.stat().st_size < 128:
        raise ValueError("subagent Codex session JSONL is missing or too small")
    event_count = 0
    session_found = session_id in path.name
    task_found = False
    with path.open("r", encoding="utf-8", errors="strict") as stream:
        for line in stream:
            if not line.strip():
                continue
            event_count += 1
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("subagent Codex session JSONL contains invalid events") from exc
            serialized = json.dumps(event, ensure_ascii=False)
            session_found = session_found or session_id in serialized
            task_found = task_found or task_id in serialized
    if not session_found or not task_found:
        raise ValueError("subagent Codex session JSONL is not bound to the session and immutable task")
    return path.as_posix(), sha256_file(path), event_count


def _load_invocation_receipt(
    run_root: Path,
    *,
    receipt_file: Path,
    stage: str,
    assignment: dict[str, Any],
    session_id: str,
    invocation: str,
    delegation_mode: str,
    session_evidence_path: str,
    session_evidence_sha256: str,
) -> tuple[dict[str, Any], str, str]:
    receipt_file = receipt_file.expanduser().resolve()
    try:
        rel = receipt_file.relative_to(run_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("subagent invocation receipt must stay inside run root") from exc
    if not receipt_file.is_file() or receipt_file.stat().st_size < 64:
        raise ValueError("subagent invocation receipt must be a physical JSON file of at least 64 bytes")
    try:
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("subagent invocation receipt must contain valid JSON") from exc
    if not isinstance(receipt, dict):
        raise ValueError("subagent invocation receipt must contain a JSON object")
    expected = {
        "schemaVersion": "3.2",
        "stage": stage,
        "workerId": assignment.get("workerId"),
        "taskId": assignment.get("taskId"),
        "sessionId": session_id.strip(),
        "delegationMode": delegation_mode,
        "invocation": invocation.strip(),
        "dispatchContractSha256": assignment.get("dispatchContractSha256"),
        "sessionEvidencePath": session_evidence_path,
        "sessionEvidenceSha256": session_evidence_sha256,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise ValueError(f"invocation receipt field {key!r} does not match the immutable assignment/invocation")
    if not isinstance(receipt.get("issuedAt"), str) or len(receipt["issuedAt"].strip()) < 10:
        raise ValueError("invocation receipt requires issuedAt")
    return receipt, rel, sha256_file(receipt_file)


def record_subagent_result(
    run_root: Path,
    *,
    stage: str,
    worker_id: str,
    session_id: str,
    invocation: str,
    invocation_receipt_file: Path,
    session_evidence_file: Path,
    evidence_file: Path,
    review_of_worker_ids: list[str] | None = None,
    task_id: str = "",
    delegation_mode: str = "native-agents",
) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError(f"unknown stage: {stage}")
    if delegation_mode != "native-agents":
        raise ValueError("delegation_mode must be native-agents")
    if "/agents" not in invocation:
        raise ValueError("native-agents invocation must contain /agents")
    if len(session_id.strip()) < 8:
        raise ValueError("independent subagent session ID must be at least 8 characters")
    plan = read_json(run_root / "orchestration" / stage / "agent-plan.json", {})
    assignment_map = {str(item.get("workerId")): item for item in plan.get("assignments", []) if isinstance(item, dict)}
    assignment = assignment_map.get(worker_id)
    if not assignment:
        raise ValueError("worker_id is not present in the immutable stage agent plan")
    if task_id and task_id != assignment.get("taskId"):
        raise ValueError("task_id does not match the planned assignment")
    dispatch_path = run_root / str(assignment.get("dispatchContractPath", ""))
    if not dispatch_path.is_file() or sha256_file(dispatch_path) != assignment.get("dispatchContractSha256"):
        raise ValueError("immutable dispatch contract is missing or modified")
    session_evidence_path, session_evidence_sha256, session_event_count = _validate_codex_session_evidence(
        session_evidence_file,
        session_id=session_id.strip(),
        task_id=str(assignment.get("taskId", "")),
    )
    receipt, receipt_rel, receipt_sha = _load_invocation_receipt(
        run_root,
        receipt_file=invocation_receipt_file,
        stage=stage,
        assignment=assignment,
        session_id=session_id,
        invocation=invocation,
        delegation_mode=delegation_mode,
        session_evidence_path=session_evidence_path,
        session_evidence_sha256=session_evidence_sha256,
    )
    evidence_file = evidence_file.resolve()
    if not evidence_file.is_file() or evidence_file.stat().st_size < 96:
        raise ValueError("subagent evidence must be a physical file of at least 96 bytes")
    try:
        evidence_rel = evidence_file.relative_to(run_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("subagent evidence must stay inside run root") from exc
    planned_reviews = [str(value) for value in assignment.get("reviewTargetWorkerIds", []) if value]
    submitted_reviews = [str(value) for value in review_of_worker_ids or [] if value]
    if sorted(submitted_reviews) != sorted(planned_reviews):
        raise ValueError("cross-review targets must exactly match the immutable ring-review assignment")
    evidence_text = evidence_file.read_text(encoding="utf-8", errors="replace")
    required_markers = [
        worker_id, str(assignment.get("taskId", "")), session_id.strip(),
        str(assignment.get("dispatchContractSha256", "")), *planned_reviews,
    ]
    missing_markers = [marker for marker in required_markers if marker and marker not in evidence_text]
    if missing_markers:
        raise ValueError(f"subagent evidence is missing immutable identity/review markers: {missing_markers}")
    planned_scopes = [str(value) for value in assignment.get("scopeIds", []) if value]
    if planned_scopes and not any(scope in evidence_text for scope in planned_scopes):
        raise ValueError("subagent evidence must mention at least one planned scope ID")
    ledger_path = run_root / "orchestration" / stage / "execution-ledger.json"
    ledger = read_json(ledger_path, {"schemaVersion": "3.2", "stage": stage, "workers": []})
    workers = [item for item in ledger.get("workers", []) if isinstance(item, dict)]
    evidence_sha = sha256_file(evidence_file)
    for item in workers:
        if item.get("workerId") == worker_id:
            continue
        if item.get("sessionId") == session_id:
            raise ValueError("each subagent must use a unique independent session ID")
        if item.get("evidenceSha256") == evidence_sha:
            raise ValueError("each subagent must produce a unique physical output hash")
        if item.get("invocationReceiptSha256") == receipt_sha:
            raise ValueError("each subagent invocation receipt must have a unique physical hash")
    record = {
        "schemaVersion": "3.2",
        "workerId": worker_id,
        "taskId": assignment.get("taskId"),
        "role": assignment.get("role"),
        "scopeIds": assignment.get("scopeIds", []),
        "delegationMode": delegation_mode,
        "invocation": invocation.strip(),
        "sessionId": session_id.strip(),
        "sessionEvidencePath": session_evidence_path,
        "sessionEvidenceSha256": session_evidence_sha256,
        "sessionEvidenceEventCount": session_event_count,
        "status": "completed",
        "dispatchContractPath": assignment.get("dispatchContractPath"),
        "dispatchContractSha256": assignment.get("dispatchContractSha256"),
        "invocationReceiptPath": receipt_rel,
        "invocationReceiptSha256": receipt_sha,
        "invocationReceiptBytes": invocation_receipt_file.stat().st_size,
        "evidencePath": evidence_rel,
        "evidenceSha256": evidence_sha,
        "evidenceBytes": evidence_file.stat().st_size,
        "reviewOfWorkerIds": planned_reviews,
        "completedAt": utc_now(),
    }
    workers = [item for item in workers if item.get("workerId") != worker_id]
    workers.append(record)
    ledger["schemaVersion"] = "3.2"
    ledger["workers"] = sorted(workers, key=lambda item: str(item.get("workerId")))
    ledger["updatedAt"] = utc_now()
    write_json(ledger_path, ledger)
    result_path = run_root / "orchestration" / stage / "results" / f"{slug(worker_id)}.json"
    write_json(result_path, record)
    return {**record, "recordPath": result_path.relative_to(run_root).as_posix(), "receipt": receipt}


def record_lead_aggregation(
    run_root: Path,
    *,
    stage: str,
    lead_agent_id: str,
    lead_session_id: str,
    session_evidence_file: Path,
    evidence_file: Path,
    accepted_worker_ids: list[str],
    resolved_conflicts: list[str] | None = None,
) -> dict[str, Any]:
    if not lead_agent_id.strip() or len(lead_session_id.strip()) < 8:
        raise ValueError("lead agent ID and an independent session ID of at least 8 characters are required")
    plan = read_json(run_root / "orchestration" / stage / "agent-plan.json", {})
    planned_ids = [str(item.get("workerId")) for item in plan.get("assignments", []) if isinstance(item, dict)]
    if set(accepted_worker_ids) != set(planned_ids):
        raise ValueError("lead aggregation must accept every planned worker exactly")
    lead_contract_path = run_root / "orchestration" / stage / "lead-contract.json"
    if not lead_contract_path.is_file():
        raise ValueError("lead contract is missing")
    lead_contract_sha = sha256_file(lead_contract_path)
    lead_contract = read_json(lead_contract_path, {})
    if lead_contract.get("planFingerprint") != plan.get("planFingerprint"):
        raise ValueError("lead contract does not match the agent plan")
    evidence_file = evidence_file.resolve()
    if not evidence_file.is_file() or evidence_file.stat().st_size < 96:
        raise ValueError("lead aggregation evidence must be a physical file of at least 96 bytes")
    try:
        rel = evidence_file.relative_to(run_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError("lead aggregation evidence must stay inside run root") from exc
    aggregation_text = evidence_file.read_text(encoding="utf-8", errors="replace")
    required_markers = [
        lead_agent_id.strip(), lead_session_id.strip(), str(plan.get("planFingerprint", "")),
        lead_contract_sha, *sorted(set(accepted_worker_ids)),
    ]
    missing_markers = [marker for marker in required_markers if marker and marker not in aggregation_text]
    if missing_markers:
        raise ValueError(f"lead aggregation evidence is missing plan/contract/agent markers: {missing_markers}")
    ledger = read_json(run_root / "orchestration" / stage / "execution-ledger.json", {})
    session_ids = {str(item.get("sessionId")) for item in ledger.get("workers", []) if isinstance(item, dict)}
    if lead_session_id in session_ids:
        raise ValueError("lead agent session must be independent from all worker sessions")
    lead_session_path, lead_session_sha256, lead_session_event_count = _validate_codex_session_evidence(
        session_evidence_file,
        session_id=lead_session_id.strip(),
        task_id=stage,
    )
    aggregation = {
        "schemaVersion": "3.2",
        "stage": stage,
        "leadAgentId": lead_agent_id.strip(),
        "leadSessionId": lead_session_id.strip(),
        "sessionEvidencePath": lead_session_path,
        "sessionEvidenceSha256": lead_session_sha256,
        "sessionEvidenceEventCount": lead_session_event_count,
        "planFingerprint": plan.get("planFingerprint"),
        "leadContractPath": lead_contract_path.relative_to(run_root).as_posix(),
        "leadContractSha256": lead_contract_sha,
        "acceptedWorkerIds": sorted(set(accepted_worker_ids)),
        "resolvedConflicts": list(resolved_conflicts or []),
        "evidencePath": rel,
        "evidenceSha256": sha256_file(evidence_file),
        "evidenceBytes": evidence_file.stat().st_size,
        "coverageDecision": "all-planned-workers-ring-reviewed-and-accepted",
        "status": "completed",
        "completedAt": utc_now(),
    }
    write_json(run_root / "orchestration" / stage / "lead-aggregation.json", aggregation)
    return aggregation


def _receipt_matches_worker(run_root: Path, worker: dict[str, Any], assignment: dict[str, Any], stage: str) -> bool:
    path = run_root / str(worker.get("invocationReceiptPath", ""))
    if not path.is_file() or worker.get("invocationReceiptSha256") != sha256_file(path):
        return False
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    expected = {
        "schemaVersion": "3.2", "stage": stage,
        "workerId": worker.get("workerId"), "taskId": assignment.get("taskId"),
        "sessionId": worker.get("sessionId"), "delegationMode": worker.get("delegationMode"),
        "invocation": worker.get("invocation"),
        "dispatchContractSha256": assignment.get("dispatchContractSha256"),
        "sessionEvidencePath": worker.get("sessionEvidencePath"),
        "sessionEvidenceSha256": worker.get("sessionEvidenceSha256"),
    }
    return isinstance(receipt, dict) and all(receipt.get(key) == value for key, value in expected.items()) and bool(receipt.get("issuedAt"))


def orchestration_issues(run_root: Path, state: dict[str, Any], stage: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    policy = read_json(run_root / "contract" / "subagent-orchestration-policy.json", {})
    canonical_policy = orchestration_policy()
    for key in [
        "mode", "minimumSubAgentsPerStage", "maximumSubAgentsPerStage", "fixedSixtyForbidden",
        "promptOnlyDelegationForbidden", "independentAgentSessionRequired", "physicalOutputEvidenceRequired",
        "uniqueSessionPerWorkerRequired", "crossReviewRequired", "fullRingCrossReviewRequired",
        "immutableDispatchContractRequired", "invocationReceiptRequired", "leadContractRequired",
        "leadAggregationRequired", "leadScaleJustificationRequired", "everyStageRequired",
    ]:
        if policy.get(key) != canonical_policy.get(key):
            issues.append({"code": "SUBAGENT_POLICY_TAMPERED", "message": 'KH_Aw blocked this operation: subagent policy tampered.', "field": key})
    plan_path = run_root / "orchestration" / stage / "agent-plan.json"
    plan = read_json(plan_path, None)
    if not isinstance(plan, dict):
        return issues + [{"code": "SUBAGENT_PLAN_MISSING", "message": 'KH_Aw blocked this operation: subagent plan missing.', "stage": stage}]
    safety_floor, _, _ = recommended_subagent_count(run_root, state, stage)
    actual_count = int(plan.get("selectedSubAgents", plan.get("recommendedSubAgents", 0)) or 0)
    if actual_count < MIN_SUBAGENTS or actual_count > MAX_SUBAGENTS:
        issues.append({"code": "SUBAGENT_COUNT_OUT_OF_RANGE", "message": 'KH_Aw blocked this operation: subagent count out of range.', "actual": actual_count})
    if actual_count < safety_floor:
        issues.append({"code": "SUBAGENT_BELOW_SAFETY_FLOOR", "message": 'KH_Aw blocked this operation: subagent below safety floor.', "floor": safety_floor, "actual": actual_count})
    justification_file: Path | None = None
    if actual_count > safety_floor:
        scale = plan.get("scaleJustification", {}) if isinstance(plan.get("scaleJustification"), dict) else {}
        justification_file = run_root / str(scale.get("path", ""))
        if (
            not justification_file.is_file() or justification_file.stat().st_size < 120
            or scale.get("sha256") != (sha256_file(justification_file) if justification_file.is_file() else "")
            or scale.get("bytes") != (justification_file.stat().st_size if justification_file.is_file() else -1)
        ):
            issues.append({"code": "SUBAGENT_SCALE_JUSTIFICATION_INVALID", "message": 'KH_Aw blocked this operation: subagent scale justification invalid.'})
    try:
        expected = canonical_agent_plan(
            run_root, state, stage,
            selected_count=actual_count,
            justification_file=justification_file if actual_count > safety_floor else None,
        )
    except ValueError:
        expected = None
    if expected is None or plan.get("planFingerprint") != expected.get("planFingerprint"):
        issues.append({"code": "SUBAGENT_DYNAMIC_SCALE_MISMATCH", "message": 'KH_Aw blocked this operation: subagent dynamic scale mismatch.'})
    assignments = [item for item in plan.get("assignments", []) if isinstance(item, dict)]
    planned_ids = [str(item.get("workerId", "")) for item in assignments]
    if len(assignments) != actual_count or len(set(planned_ids)) != len(planned_ids) or any(not value for value in planned_ids):
        issues.append({"code": "SUBAGENT_ASSIGNMENT_INVALID", "message": 'KH_Aw blocked this operation: subagent assignment invalid.'})
    expected_map = {str(item.get("workerId")): item for item in (expected or {}).get("assignments", []) if isinstance(item, dict)}
    for assignment in assignments:
        worker_id = str(assignment.get("workerId", ""))
        exp = expected_map.get(worker_id, {})
        for key in ["taskId", "role", "scopeIds", "reviewTargetWorkerIds"]:
            if assignment.get(key) != exp.get(key):
                issues.append({"code": "SUBAGENT_ASSIGNMENT_TAMPERED", "message": 'KH_Aw blocked this operation: subagent assignment tampered.', "workerId": worker_id, "field": key})
        dispatch_path = run_root / str(assignment.get("dispatchContractPath", ""))
        expected_dispatch = _dispatch_payload(stage, plan, assignment)
        dispatch_ok = dispatch_path.is_file() and assignment.get("dispatchContractSha256") == sha256_file(dispatch_path)
        if dispatch_ok:
            dispatch_ok = read_json(dispatch_path, {}) == expected_dispatch
        if not dispatch_ok:
            issues.append({"code": "SUBAGENT_DISPATCH_CONTRACT_INVALID", "message": 'KH_Aw blocked this operation: subagent dispatch contract invalid.', "workerId": worker_id})
    lead_contract_path = run_root / "orchestration" / stage / "lead-contract.json"
    lead_contract = read_json(lead_contract_path, None)
    lead_contract_sha = sha256_file(lead_contract_path) if lead_contract_path.is_file() else ""
    if not isinstance(lead_contract, dict) or lead_contract.get("planFingerprint") != plan.get("planFingerprint") or set(lead_contract.get("requiredWorkerIds", [])) != set(planned_ids):
        issues.append({"code": "LEAD_AGENT_CONTRACT_INVALID", "message": 'KH_Aw blocked this operation: lead agent contract invalid.'})

    ledger = read_json(run_root / "orchestration" / stage / "execution-ledger.json", {})
    workers = [item for item in ledger.get("workers", []) if isinstance(item, dict)]
    if len(workers) != actual_count:
        issues.append({"code": "SUBAGENT_EXECUTION_COUNT_INCOMPLETE", "message": 'KH_Aw blocked this operation: subagent execution count incomplete.', "planned": actual_count, "completed": len(workers)})
    worker_ids = [str(item.get("workerId", "")) for item in workers]
    sessions = [str(item.get("sessionId", "")) for item in workers]
    output_hashes = [str(item.get("evidenceSha256", "")) for item in workers]
    receipt_hashes = [str(item.get("invocationReceiptSha256", "")) for item in workers]
    if set(worker_ids) != set(planned_ids):
        issues.append({"code": "SUBAGENT_WORKER_COVERAGE_INCOMPLETE", "message": 'KH_Aw blocked this operation: subagent worker coverage incomplete.'})
    if len(set(sessions)) != len(sessions) or any(not value for value in sessions):
        issues.append({"code": "SUBAGENT_SESSION_NOT_INDEPENDENT", "message": 'KH_Aw blocked this operation: subagent session not independent.'})
    if len(set(output_hashes)) != len(output_hashes) or any(not value for value in output_hashes):
        issues.append({"code": "SUBAGENT_OUTPUT_DUPLICATED", "message": 'KH_Aw blocked this operation: subagent output duplicated.'})
    if len(set(receipt_hashes)) != len(receipt_hashes) or any(not value for value in receipt_hashes):
        issues.append({"code": "SUBAGENT_INVOCATION_RECEIPT_DUPLICATED", "message": 'KH_Aw blocked this operation: subagent invocation receipt duplicated.'})
    assignment_map = {str(item.get("workerId")): item for item in assignments}
    reviewed_targets: list[str] = []
    for worker in workers:
        worker_id = str(worker.get("workerId", ""))
        assignment = assignment_map.get(worker_id, {})
        if worker.get("status") != "completed" or worker.get("taskId") != assignment.get("taskId") or worker.get("role") != assignment.get("role"):
            issues.append({"code": "SUBAGENT_RECORD_INVALID", "message": 'KH_Aw blocked this operation: subagent record invalid.', "workerId": worker_id})
        if worker.get("delegationMode") != "native-agents":
            issues.append({"code": "SUBAGENT_DELEGATION_NOT_AI", "message": 'KH_Aw blocked this operation: subagent delegation not ai.', "workerId": worker_id})
        if "/agents" not in str(worker.get("invocation", "")):
            issues.append({"code": "SUBAGENT_NATIVE_INVOCATION_INVALID", "message": 'KH_Aw blocked this operation: subagent native invocation invalid.', "workerId": worker_id})
        session_path = Path(str(worker.get("sessionEvidencePath", ""))).expanduser()
        if (
            not session_path.is_file()
            or "/.codex/sessions/" not in session_path.as_posix().lower()
            or not session_path.name.lower().startswith("rollout-")
            or worker.get("sessionEvidenceSha256") != (sha256_file(session_path) if session_path.is_file() else "")
            or int(worker.get("sessionEvidenceEventCount", 0) or 0) < 1
        ):
            issues.append({
                "code": "SUBAGENT_CODEX_SESSION_EVIDENCE_INVALID",
                "message": "Each worker must remain bound to a physical Codex rollout JSONL session.",
                "workerId": worker_id,
            })
        path = run_root / str(worker.get("evidencePath", ""))
        if not path.is_file() or path.stat().st_size < 96 or worker.get("evidenceSha256") != (sha256_file(path) if path.is_file() else ""):
            issues.append({"code": "SUBAGENT_PHYSICAL_EVIDENCE_INVALID", "message": 'KH_Aw blocked this operation: subagent physical evidence invalid.', "workerId": worker_id})
        if worker.get("dispatchContractSha256") != assignment.get("dispatchContractSha256"):
            issues.append({"code": "SUBAGENT_DISPATCH_LINK_INVALID", "message": 'KH_Aw blocked this operation: subagent dispatch link invalid.', "workerId": worker_id})
        if not _receipt_matches_worker(run_root, worker, assignment, stage):
            issues.append({"code": "SUBAGENT_INVOCATION_RECEIPT_INVALID", "message": 'KH_Aw blocked this operation: subagent invocation receipt invalid.', "workerId": worker_id})
        reviewed = [str(value) for value in worker.get("reviewOfWorkerIds", []) if value]
        expected_reviewed = [str(value) for value in assignment.get("reviewTargetWorkerIds", []) if value]
        if reviewed != expected_reviewed or worker_id in reviewed:
            issues.append({"code": "SUBAGENT_RING_REVIEW_INVALID", "message": 'KH_Aw blocked this operation: subagent ring review invalid.', "workerId": worker_id})
        reviewed_targets.extend(reviewed)
    if workers and set(reviewed_targets) != set(planned_ids):
        issues.append({"code": "SUBAGENT_RING_REVIEW_COVERAGE_INCOMPLETE", "message": 'KH_Aw blocked this operation: subagent ring review coverage incomplete.'})

    aggregation = read_json(run_root / "orchestration" / stage / "lead-aggregation.json", None)
    if not isinstance(aggregation, dict):
        issues.append({"code": "LEAD_AGENT_AGGREGATION_MISSING", "message": 'KH_Aw blocked this operation: lead agent aggregation missing.'})
    else:
        if aggregation.get("status") != "completed" or set(aggregation.get("acceptedWorkerIds", [])) != set(planned_ids):
            issues.append({"code": "LEAD_AGENT_AGGREGATION_INCOMPLETE", "message": 'KH_Aw blocked this operation: lead agent aggregation incomplete.'})
        if aggregation.get("leadSessionId") in set(sessions) or not str(aggregation.get("leadSessionId", "")):
            issues.append({"code": "LEAD_AGENT_SESSION_NOT_INDEPENDENT", "message": 'KH_Aw blocked this operation: lead agent session not independent.'})
        if aggregation.get("planFingerprint") != plan.get("planFingerprint") or aggregation.get("leadContractSha256") != lead_contract_sha:
            issues.append({"code": "LEAD_AGENT_PLAN_CONTRACT_LINK_INVALID", "message": 'KH_Aw blocked this operation: lead agent plan contract link invalid.'})
        lead_session_path = Path(str(aggregation.get("sessionEvidencePath", ""))).expanduser()
        if (
            not lead_session_path.is_file()
            or "/.codex/sessions/" not in lead_session_path.as_posix().lower()
            or not lead_session_path.name.lower().startswith("rollout-")
            or aggregation.get("sessionEvidenceSha256") != (sha256_file(lead_session_path) if lead_session_path.is_file() else "")
            or int(aggregation.get("sessionEvidenceEventCount", 0) or 0) < 1
        ):
            issues.append({
                "code": "LEAD_AGENT_CODEX_SESSION_EVIDENCE_INVALID",
                "message": "The stage lead must remain bound to a physical Codex rollout JSONL session.",
            })
        path = run_root / str(aggregation.get("evidencePath", ""))
        if not path.is_file() or path.stat().st_size < 96 or aggregation.get("evidenceSha256") != (sha256_file(path) if path.is_file() else ""):
            issues.append({"code": "LEAD_AGENT_AGGREGATION_EVIDENCE_INVALID", "message": 'KH_Aw blocked this operation: lead agent aggregation evidence invalid.'})
    return issues
