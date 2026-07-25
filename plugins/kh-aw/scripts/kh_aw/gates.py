from __future__ import annotations

import json
import re
import struct
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .capabilities import NATIVE_CAPABILITIES, capability_records_for_stage
from .contracts import RESEARCH_CATEGORIES, STAGES, scan_forbidden_manual_keys, stage_status_passed
from .copy_audit import build_copy_audit
from .language_policy import (
    internal_language_issues,
    korean_ui_character_count,
    language_policy as canonical_language_policy,
)
from .targeting import TARGET_PIPELINES
from .tooling import canonical_required_tool_ids, command_forbidden, directory_artifact_record, required_tool_ids
from .run_lock import verify_run_lock
from .protection import compare_snapshot
from .orchestration import orchestration_issues
from .util import (
    exact_instruction_lines,
    is_inside,
    nonempty,
    read_json,
    safe_resolve,
    sha256_file,
    unique_nonempty,
    utc_now,
    write_json,
)

SEARCH_HOSTS = {
    "duckduckgo.com", "www.duckduckgo.com", "google.com", "www.google.com",
    "bing.com", "www.bing.com", "search.naver.com", "search.daum.net",
}
BLOCK_PAGE_MARKERS = {
    "access denied", "captcha", "verify you are human", "enable javascript",
    "robot check", "cloudflare ray id", "\ub85c\uadf8\uc778\uc774 \ud544\uc694", "\uc811\uadfc\uc774 \uac70\ubd80",
}
PUBLIC_VISIBILITIES = {"public", "authenticated", "customer", "user"}
STATIC_EXCEPTION_VISIBILITIES = {"legal", "system", "internal", "admin-static"}


def canonical_issue_message(code: str) -> str:
    words = str(code).strip().replace("_", " ").lower()
    return f"KH_Aw blocked this stage: {words}."


def issue(code: str, message: str, severity: str = "major", **evidence: Any) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, "evidence": evidence}


def _read_required_json(path: Path, issues: list[dict[str, Any]], code: str) -> Any:
    value = read_json(path, None)
    if value is None:
        issues.append(issue(code, "KH_Aw blocked this stage because required evidence is incomplete."))
    return value


def _run_path(run_root: Path, raw: str) -> Path:
    path = Path(str(raw or ""))
    return path.resolve() if path.is_absolute() else (run_root / path).resolve()


def _file_ok(run_root: Path, raw: str, min_bytes: int = 1) -> bool:
    if not raw:
        return False
    path = _run_path(run_root, raw)
    return is_inside(path, run_root) and path.is_file() and path.stat().st_size >= min_bytes


def _png_info(path: Path) -> tuple[int, int] | None:
    try:
        data = path.read_bytes()[:24]
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
            return None
        return struct.unpack(">II", data[16:24])
    except OSError:
        return None


def _ids(items: Any, key: str) -> list[str]:
    if not isinstance(items, list):
        return []
    return [str(item.get(key, "")).strip() for item in items if isinstance(item, dict)]


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    dup: set[str] = set()
    for value in values:
        if value in seen:
            dup.add(value)
        seen.add(value)
    return sorted(dup)


def _marker_has_executable_context(text: str, marker: str) -> bool:
    if not marker or marker not in text:
        return False
    comment_prefixes = ("//", "#", "<!--", "/*", "*", "--")
    for line in text.splitlines():
        if marker not in line:
            continue
        stripped = line.strip()
        if not stripped.startswith(comment_prefixes):
            return True
    return False


def _require_no_omissions(payload: Any, issues: list[dict[str, Any]], label: str) -> None:
    if isinstance(payload, dict) and payload.get("omissions"):
        issues.append(issue("DECLARED_OMISSIONS_REMAIN", canonical_issue_message('DECLARED_OMISSIONS_REMAIN'), omissions=payload.get("omissions")))


def _require_unique_ids(items: Any, key: str, code: str, label: str, issues: list[dict[str, Any]]) -> set[str]:
    values = _ids(items, key)
    empty_count = sum(1 for value in values if not value)
    duplicates = _duplicates([value for value in values if value])
    if empty_count or duplicates or not values:
        issues.append(issue(code, "KH_Aw blocked this stage because required evidence is incomplete.", emptyCount=empty_count, duplicates=duplicates, count=len(values)))
    return {value for value in values if value}


def _all_previous_passed(state: dict[str, Any], stage: str) -> tuple[bool, list[str]]:
    index = STAGES.index(stage)
    missing = [name for name in STAGES[:index] if not stage_status_passed(state.get("stageStatus", {}).get(name, ""))]
    return not missing, missing


def _gate_target_pipeline(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    target = str(state.get("targetPipeline", "")).strip()
    if target not in TARGET_PIPELINES:
        return [issue("TARGET_PIPELINE_INVALID", "targetPipeline must be one of the supported KH_Aw target types.", targetPipeline=target)]
    if target == "unknown-needs-confirmation":
        return [issue("TARGET_PIPELINE_UNRESOLVED", "KH_Aw could not determine whether this is an app, web, native, or cross-platform project. Lock an explicit target before work continues.")]
    return []


def _gate_copy_audit(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    if state.get("analysisMode") != "analysis-folder-provided":
        return issues
    analysis_root = Path(str(state.get("analysisFolder", "")))
    product_root = Path(str(state.get("projectRoot", "")))
    if not analysis_root.is_dir() or not product_root.is_dir():
        return issues
    audit_path = run_root / "audit" / "copy-audit-ledger.json"
    audit = build_copy_audit(
        analysis_root,
        product_root,
        audit_path,
        target_pipeline=str(state.get("targetPipeline", "")),
    )
    if audit.get("forbiddenCopyCount", 0):
        issues.append(issue(
            "SOURCE_BULK_COPY_DETECTED",
            "Files from the read-only analysis folder were copied into the product output without approved runtime or bridge justification.",
            forbiddenCopyCount=audit.get("forbiddenCopyCount"),
            nativeForbiddenCopyCount=audit.get("nativeForbiddenCopyCount"),
            auditPath=audit_path.relative_to(run_root).as_posix(),
        ))
    return issues


def _gate_dynamic_page_inventory(run_root: Path, inventory: Any, issues: list[dict[str, Any]]) -> None:
    pages = inventory.get("pages", []) if isinstance(inventory, dict) else []
    if not isinstance(pages, list) or not pages:
        issues.append(issue("DYNAMIC_PAGE_INVENTORY_MISSING", "page-inventory.json must contain project-derived pages instead of a fixed or empty screen list."))
        return
    for page in pages:
        if not isinstance(page, dict):
            continue
        pid = str(page.get("pageId", ""))
        for field in ["sourceEvidence", "routeOrEntry", "requiredRegions", "requiredFields", "requiredActions", "requiredStates", "derivedFrom", "requiredBecause"]:
            if not nonempty(page.get(field)):
                issues.append(issue("PAGE_INVENTORY_DERIVATION_INCOMPLETE", "Each page must explain where it came from and what it requires; hardcoded screen groups are not allowed.", pageId=pid, field=field))
    candidate_path = _run_path(run_root, str(inventory.get("candidateInventoryPath", "")))
    candidates_payload = read_json(candidate_path, None)
    if not isinstance(candidates_payload, dict):
        issues.append(issue("PAGE_CANDIDATE_INVENTORY_MISSING", "Dynamic page candidate collection must run before page design."))
        return
    candidate_ids = {
        str(item.get("candidateId"))
        for item in candidates_payload.get("candidates", [])
        if isinstance(item, dict) and item.get("candidateId")
    }
    mapped_ids = {
        str(value)
        for page in pages if isinstance(page, dict)
        for value in page.get("sourceCandidateIds", [])
        if str(value)
    }
    excluded_rows = inventory.get("excludedCandidates", [])
    excluded_ids: set[str] = set()
    for row in excluded_rows if isinstance(excluded_rows, list) else []:
        if not isinstance(row, dict):
            continue
        candidate_id = str(row.get("candidateId", ""))
        excluded_ids.add(candidate_id)
        if len(str(row.get("reason", "")).strip()) < 50 or not nonempty(row.get("evidence")):
            issues.append(issue("PAGE_CANDIDATE_EXCLUSION_UNPROVEN", "Excluded page candidates need a concrete reason and evidence.", candidateId=candidate_id))
    unknown = sorted((mapped_ids | excluded_ids) - candidate_ids)
    missing = sorted(candidate_ids - mapped_ids - excluded_ids)
    if unknown:
        issues.append(issue("PAGE_CANDIDATE_REFERENCE_INVALID", "Page inventory references unknown candidate IDs.", candidateIds=unknown))
    if missing:
        issues.append(issue("PAGE_CANDIDATE_COVERAGE_INCOMPLETE", "Every automatically discovered page candidate must be mapped or explicitly excluded.", candidateIds=missing[:200], count=len(missing)))


REQUIREMENT_LEDGER_BY_STAGE = {
    "analyze": "analysis/analysis-ledger.json",
    "research": "evidence/research-plan.json",
    "design": "design/design-ledger.json",
    "implement": "implementation/implementation-ledger.json",
    "review": "review/review.json",
    "test": "test/test-report.json",
    "release": "release/release.json",
}


def _gate_requirement_coverage(run_root: Path, state: dict[str, Any], stage: str) -> list[dict[str, Any]]:
    relative = REQUIREMENT_LEDGER_BY_STAGE.get(stage)
    if not relative:
        return []
    issues: list[dict[str, Any]] = []
    requirements = read_json(run_root / "contract" / "requirements.json", {})
    expected = {
        str(item.get("id"))
        for item in requirements.get("requirements", [])
        if isinstance(item, dict) and item.get("id")
    }
    ledger = read_json(run_root / relative, {})
    coverage = ledger.get("requirementCoverage", []) if isinstance(ledger, dict) else []
    rows = {
        str(item.get("requirementId")): item
        for item in coverage
        if isinstance(item, dict) and item.get("requirementId")
    }
    if set(rows) != expected or len(coverage) != len(expected):
        issues.append(issue(
            "REQUIREMENT_STAGE_COVERAGE_INCOMPLETE",
            "Every preserved user requirement must have exactly one stage coverage row.",
            stage=stage,
            expected=sorted(expected),
            actual=sorted(rows),
        ))
    project_root = Path(str(state.get("projectRoot", "")))
    for requirement_id, row in rows.items():
        status = str(row.get("status", ""))
        if status not in {"covered", "partial", "missing", "blocked", "not_applicable"}:
            issues.append(issue("REQUIREMENT_STATUS_INVALID", "Requirement status is invalid.", stage=stage, requirementId=requirement_id, status=status))
            continue
        if status in {"partial", "missing", "blocked"}:
            issues.append(issue("REQUIREMENT_NOT_FULLY_COVERED", "A partial, missing, or blocked requirement prevents stage completion.", stage=stage, requirementId=requirement_id, status=status))
        evidence_paths = [str(value) for value in row.get("evidencePaths", []) if str(value).strip()]
        if status == "covered":
            if not evidence_paths or len(str(row.get("verificationMethod", "")).strip()) < 10:
                issues.append(issue("REQUIREMENT_EVIDENCE_MISSING", "Covered requirements need physical evidence paths and a verification method.", stage=stage, requirementId=requirement_id))
            for raw in evidence_paths:
                candidate = safe_resolve(raw, project_root)
                if not candidate.exists():
                    candidate = _run_path(run_root, raw)
                if not candidate.exists():
                    issues.append(issue("REQUIREMENT_EVIDENCE_PATH_INVALID", "Requirement evidence path does not exist.", stage=stage, requirementId=requirement_id, path=raw))
        if status == "not_applicable" and len(str(row.get("reason", "")).strip()) < 30:
            issues.append(issue("REQUIREMENT_NOT_APPLICABLE_REASON_MISSING", "A not-applicable requirement needs a concrete project-specific reason.", stage=stage, requirementId=requirement_id))
    return issues


def _gate_target_artifact_shape(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    target = str(state.get("targetPipeline", ""))
    project = Path(str(state.get("projectRoot", "")))
    if not project.is_dir():
        return issues
    html_files = list(project.rglob("*.html"))
    js_files = list(project.rglob("*.js")) + list(project.rglob("*.mjs")) + list(project.rglob("*.ts")) + list(project.rglob("*.tsx"))
    css_files = list(project.rglob("*.css")) + list(project.rglob("*.scss"))
    image_files = [p for p in project.rglob("*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}]
    if target in {"web-responsive", "app-mobile-webview", "cross-platform"}:
        if not html_files and not any((project / name).is_file() for name in ["package.json", "vite.config.ts", "next.config.js", "next.config.mjs"]):
            issues.append(issue("WEB_ENTRYPOINT_MISSING", "Web targets must include a real web entrypoint, route system, or build configuration."))
        if not js_files:
            issues.append(issue("WEB_SCRIPT_SURFACE_MISSING", "Web targets must include real script/application files, not only static claims."))
        if not css_files:
            issues.append(issue("WEB_STYLE_SURFACE_MISSING", "Web targets must include real styling files for responsive and visual verification."))
    if target in {"app-mobile-webview", "cross-platform"}:
        if not any(project.rglob("AndroidManifest.xml")):
            issues.append(issue("ANDROID_MANIFEST_MISSING_FOR_WEBVIEW_APP", "Android WebView targets must be recognizable Android Studio projects."))
        asset_html = list((project / "app" / "src" / "main" / "assets").rglob("*.html")) if (project / "app" / "src" / "main" / "assets").is_dir() else []
        if not asset_html:
            issues.append(issue("WEBVIEW_ASSET_HTML_MISSING", "Android WebView targets must package HTML files under app/src/main/assets."))
        native_screen_files = [
            p for p in project.rglob("*")
            if p.suffix.lower() in {".kt", ".java"} and any(token in p.name for token in ["Activity", "Fragment", "ViewModel"])
        ]
        bridge_files = [p for p in native_screen_files if any(token in p.as_posix().lower() for token in ["bridge", "webview", "firebase", "naver", "gemma", "auth"])]
        if len(native_screen_files) - len(bridge_files) > 5:
            issues.append(issue("WEBVIEW_NATIVE_SCREEN_SURFACE_TOO_LARGE", "Android WebView output must not remain primarily native Activity/Fragment/ViewModel screens.", nativeScreenFiles=len(native_screen_files), bridgeLikeFiles=len(bridge_files)))
        native_sources = [
            path for path in (project / "app" / "src" / "main").rglob("*")
            if path.suffix.lower() in {".kt", ".java"} and path.is_file()
        ] if (project / "app" / "src" / "main").is_dir() else []
        native_text = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in native_sources
        )
        if "WebView" not in native_text or "loadUrl" not in native_text or "android_asset" not in native_text:
            issues.append(issue("WEBVIEW_ENTRYPOINT_NOT_WIRED", "Android WebView targets must physically load the packaged HTML entrypoint from android_asset."))
        if "addJavascriptInterface" not in native_text and "@JavascriptInterface" not in native_text:
            issues.append(issue("WEBVIEW_BRIDGE_NOT_WIRED", "Android WebView targets must provide a physical JavaScript bridge for native capabilities."))
    if target in {"web-responsive", "app-mobile-webview", "cross-platform"} and not image_files:
        issues.append(issue("VISUAL_ASSET_SURFACE_MISSING", "Public app/web targets must include physical image assets when the design contract requires imagery."))
    return issues



def _gate_native_capabilities(run_root: Path, stage: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    required, records = capability_records_for_stage(run_root, stage)
    record_map = {str(item.get("capabilityId")): item for item in records if isinstance(item, dict)}
    for definition in required:
        capability_id = str(definition.get("id", ""))
        record = record_map.get(capability_id)
        if not record:
            issues.append(issue("NATIVE_CAPABILITY_EVIDENCE_MISSING", canonical_issue_message('NATIVE_CAPABILITY_EVIDENCE_MISSING'), stage=stage, capabilityId=capability_id, preferredSlash=definition.get("preferredSlash")))
            continue
        path = _run_path(run_root, str(record.get("evidencePath", "")))
        if not path.is_file() or not is_inside(path, run_root) or path.stat().st_size < 16:
            issues.append(issue("NATIVE_CAPABILITY_EVIDENCE_INVALID", canonical_issue_message('NATIVE_CAPABILITY_EVIDENCE_INVALID'), capabilityId=capability_id, path=record.get("evidencePath")))
            continue
        if record.get("evidenceSha256") != sha256_file(path):
            issues.append(issue("NATIVE_CAPABILITY_HASH_MISMATCH", canonical_issue_message('NATIVE_CAPABILITY_HASH_MISMATCH'), capabilityId=capability_id))
        preferred = str(definition.get("preferredSlash", ""))
        if record.get("mode") != "native":
            issues.append(issue(
                "NATIVE_SLASH_REQUIRED",
                "A diagnostic fallback cannot satisfy a required Codex slash capability.",
                capabilityId=capability_id,
                preferredSlash=preferred,
                recordedMode=record.get("mode"),
            ))
        if not str(record.get("sessionId", "")).strip() or preferred not in str(record.get("invocation", "")):
            issues.append(issue(
                "NATIVE_CAPABILITY_SESSION_LINK_INVALID",
                "Native slash evidence must identify the Codex session and exact slash invocation.",
                capabilityId=capability_id,
                preferredSlash=preferred,
            ))
        session_path = Path(str(record.get("sessionEvidencePath", ""))).expanduser()
        session_text = ""
        if session_path.is_file():
            session_text = session_path.read_text(encoding="utf-8", errors="replace")
        if (
            not session_path.is_file()
            or "/.codex/sessions/" not in session_path.as_posix().lower()
            or not session_path.name.lower().startswith("rollout-")
            or session_path.suffix.lower() != ".jsonl"
            or record.get("sessionEvidenceSha256") != (sha256_file(session_path) if session_path.is_file() else "")
            or int(record.get("sessionEvidenceEventCount", 0) or 0) < 1
            or str(record.get("sessionId", "")) not in session_text
            or preferred not in session_text
        ):
            issues.append(issue(
                "NATIVE_CAPABILITY_SESSION_EVIDENCE_INVALID",
                "Native slash evidence must be backed by the current physical Codex rollout JSONL.",
                capabilityId=capability_id,
            ))
        if record.get("mode") not in {"native", "fallback"} or record.get("status") != "verified" or not str(record.get("invocation", "")).strip():
            issues.append(issue("NATIVE_CAPABILITY_RECORD_INVALID", canonical_issue_message('NATIVE_CAPABILITY_RECORD_INVALID'), capabilityId=capability_id))
    return issues


def _physical_evidence_item(run_root: Path, item: Any, execution_ids: set[str], label: str, issues: list[dict[str, Any]]) -> None:
    if not isinstance(item, dict) or item.get("pass") is not True:
        issues.append(issue("PHYSICAL_TEST_EVIDENCE_INVALID", canonical_issue_message('PHYSICAL_TEST_EVIDENCE_INVALID'), item=item))
        return
    path_raw = str(item.get("evidencePath", ""))
    path = _run_path(run_root, path_raw)
    if not path.is_file() or not is_inside(path, run_root) or path.stat().st_size < 1:
        issues.append(issue("PHYSICAL_TEST_EVIDENCE_MISSING", canonical_issue_message('PHYSICAL_TEST_EVIDENCE_MISSING'), path=path_raw))
        return
    if item.get("evidenceSha256") != sha256_file(path):
        issues.append(issue("PHYSICAL_TEST_EVIDENCE_HASH_MISMATCH", canonical_issue_message('PHYSICAL_TEST_EVIDENCE_HASH_MISMATCH'), path=path_raw))
    linked = set(unique_nonempty(item.get("toolExecutionIds", [])))
    if not linked or not linked.issubset(execution_ids):
        issues.append(issue("PHYSICAL_TEST_TOOL_LINK_INVALID", canonical_issue_message('PHYSICAL_TEST_TOOL_LINK_INVALID'), linked=sorted(linked)))


def gate_intake(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    requirements = _read_required_json(run_root / "contract" / "requirements.json", issues, "REQUIREMENTS_MISSING") or {}
    instruction_path = Path(str(state.get("instructionsFile", "")))
    instructions = instruction_path.read_text(encoding="utf-8", errors="replace") if instruction_path.is_file() else ""
    expected = exact_instruction_lines(instructions)
    coverage = requirements.get("rawInstructionCoverage", []) if isinstance(requirements, dict) else []
    actual = [str(item.get("sourceText", "")).rstrip() for item in coverage if isinstance(item, dict)]
    if not expected:
        issues.append(issue("USER_INSTRUCTIONS_EMPTY", canonical_issue_message('USER_INSTRUCTIONS_EMPTY')))
    if expected != actual:
        issues.append(issue(
            "RAW_INSTRUCTION_ONE_TO_ONE_REQUIRED",
            canonical_issue_message('RAW_INSTRUCTION_ONE_TO_ONE_REQUIRED'),
            expectedCount=len(expected), actualCount=len(actual),
        ))
    requirements_list = requirements.get("requirements", []) if isinstance(requirements, dict) else []
    raw_ids = _require_unique_ids(coverage, "id", "RAW_IDS_INVALID", 'raw instruction', issues)
    req_ids = _require_unique_ids(requirements_list, "id", "REQUIREMENT_IDS_INVALID", 'requirement', issues)
    if len(requirements_list) != len(expected):
        issues.append(issue("REQUIREMENT_COUNT_MISMATCH", canonical_issue_message('REQUIREMENT_COUNT_MISMATCH'), expected=len(expected), actual=len(requirements_list)))
    for item in coverage:
        if not isinstance(item, dict):
            continue
        linked = set(unique_nonempty(item.get("requirementIds", [])))
        if not linked or not linked.issubset(req_ids):
            issues.append(issue("RAW_REQUIREMENT_LINK_INVALID", canonical_issue_message('RAW_REQUIREMENT_LINK_INVALID'), rawId=item.get("id"), linked=sorted(linked)))
    source_ids = {str(item.get("source", "")) for item in requirements_list if isinstance(item, dict)}
    if source_ids != raw_ids:
        issues.append(issue("REQUIREMENT_SOURCE_COVERAGE_INCOMPLETE", canonical_issue_message('REQUIREMENT_SOURCE_COVERAGE_INCOMPLETE'), expected=sorted(raw_ids), actual=sorted(source_ids)))
    forbidden = scan_forbidden_manual_keys(requirements)
    if forbidden:
        issues.append(issue("MANUAL_DESIGN_SELECTION_FORBIDDEN", canonical_issue_message('MANUAL_DESIGN_SELECTION_FORBIDDEN'), paths=forbidden))
    tool_policy = _read_required_json(run_root / "contract" / "tool-policy.json", issues, "TOOL_POLICY_MISSING") or {}
    if tool_policy.get("apkInstallation", {}).get("status") != "forbidden":
        issues.append(issue("APK_INSTALL_EXCLUSION_NOT_LOCKED", canonical_issue_message('APK_INSTALL_EXCLUSION_NOT_LOCKED')))
    policy_ids = [str(item.get("id", "")) for item in tool_policy.get("requiredTools", []) if isinstance(item, dict) and item.get("required") is True]
    canonical_tool_ids = canonical_required_tool_ids(
        str(state.get("targetPipeline", "web-responsive")),
        Path(str(state.get("projectRoot", "."))).resolve(),
    )
    if policy_ids != canonical_tool_ids:
        issues.append(issue("TARGET_TOOL_POLICY_TAMPERED", canonical_issue_message('TARGET_TOOL_POLICY_TAMPERED'), expected=canonical_tool_ids, actual=policy_ids))
    capability_policy = _read_required_json(run_root / "contract" / "native-capability-policy.json", issues, "NATIVE_CAPABILITY_POLICY_MISSING") or {}
    configured_language_policy = _read_required_json(run_root / "contract" / "language-policy.json", issues, "LANGUAGE_POLICY_MISSING") or {}
    expected_language_policy = canonical_language_policy()
    for key, value in expected_language_policy.items():
        if key == "schemaVersion":
            continue
        if configured_language_policy.get(key) != value:
            issues.append(issue(
                "LANGUAGE_POLICY_TAMPERED",
                "Internal English and user-facing Korean language boundaries are immutable.",
                field=key,
                expected=value,
                actual=configured_language_policy.get(key),
            ))
    policy_capability_ids = [str(item.get("id", "")) for item in capability_policy.get("capabilities", []) if isinstance(item, dict) and item.get("required") is True]
    canonical_capability_ids = [str(item.get("id", "")) for item in NATIVE_CAPABILITIES if item.get("required") is True]
    if capability_policy.get("requiredEvidenceMode") != "native" or capability_policy.get("fallbackSatisfiesRequiredCapability") is not False:
        issues.append(issue(
            "NATIVE_CAPABILITY_POLICY_TAMPERED",
            "Required slash capabilities must remain native-only and fail closed when unavailable.",
        ))
    if policy_capability_ids != canonical_capability_ids:
        issues.append(issue("NATIVE_CAPABILITY_POLICY_TAMPERED", canonical_issue_message('NATIVE_CAPABILITY_POLICY_TAMPERED'), expected=canonical_capability_ids, actual=policy_capability_ids))
    _require_no_omissions(requirements, issues, 'requirement contract')
    return issues


def gate_analyze(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    requirements = _read_required_json(run_root / "contract" / "requirements.json", issues, "REQUIREMENTS_MISSING") or {}
    inventory = _read_required_json(run_root / "inventory" / "inventory-summary.json", issues, "ANALYSIS_INVENTORY_MISSING") or {}
    ledger = _read_required_json(run_root / "analysis" / "analysis-ledger.json", issues, "ANALYSIS_LEDGER_MISSING") or {}
    req_ids = {str(item.get("id", "")) for item in requirements.get("requirements", []) if isinstance(item, dict) and item.get("id")}
    project_kind = str(ledger.get("projectKind", "")) if isinstance(ledger, dict) else ""
    file_count = int(inventory.get("fileCount", 0) or 0)
    if project_kind not in {"existing", "greenfield"}:
        issues.append(issue("PROJECT_KIND_UNRESOLVED", canonical_issue_message('PROJECT_KIND_UNRESOLVED')))
    if file_count <= 0 and not (project_kind == "greenfield" and len(str(ledger.get("greenfieldJustification", ""))) >= 30):
        issues.append(issue("ANALYSIS_INVENTORY_EMPTY", canonical_issue_message('ANALYSIS_INVENTORY_EMPTY')))
    inventory_jsonl = Path(str(inventory.get("inventoryJsonl", "")))
    inventory_paths: set[str] = set()
    if not inventory_jsonl.is_file():
        issues.append(issue("ANALYSIS_INVENTORY_JSONL_MISSING", canonical_issue_message('ANALYSIS_INVENTORY_JSONL_MISSING')))
    else:
        inventory_paths: set[str] = set()
        with inventory_jsonl.open("r", encoding="utf-8", errors="replace") as stream:
            inventory_rows = 0
            for raw_line in stream:
                inventory_rows += 1
                try:
                    row = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict) and row.get("path"):
                    inventory_paths.add(str(row["path"]))
        if file_count != inventory_rows:
            issues.append(issue("ANALYSIS_INVENTORY_COUNT_MISMATCH", canonical_issue_message('ANALYSIS_INVENTORY_COUNT_MISMATCH')))
    required_fields = [
        "projectSummary", "techStack", "architecture", "requirementCoverage", "pageInventory",
        "fieldInventory", "logicInventory", "featureInventory", "fileFindings", "logicFindings",
        "securityFindings", "performanceFindings", "designFindings", "strengths",
        "weaknesses", "risks", "upgradeTargets",
    ]
    for field in required_fields:
        if not nonempty(ledger.get(field)):
            issues.append(issue("ANALYSIS_FIELD_INCOMPLETE", canonical_issue_message('ANALYSIS_FIELD_INCOMPLETE'), field=field))
    if ledger.get("projectStructure", {}).get("fileCount") != file_count:
        issues.append(issue("ANALYSIS_FILE_COUNT_TRACE_MISMATCH", canonical_issue_message('ANALYSIS_FILE_COUNT_TRACE_MISMATCH'), inventory=file_count, ledger=ledger.get("projectStructure", {}).get("fileCount")))
    coverage_ids = {str(item.get("requirementId", item.get("id", ""))) for item in ledger.get("requirementCoverage", []) if isinstance(item, dict)}
    if coverage_ids != req_ids:
        issues.append(issue("ANALYSIS_REQUIREMENT_COVERAGE_INCOMPLETE", canonical_issue_message('ANALYSIS_REQUIREMENT_COVERAGE_INCOMPLETE'), expected=sorted(req_ids), actual=sorted(coverage_ids)))
    page_ids = _require_unique_ids(ledger.get("pageInventory", []), "pageId", "ANALYSIS_PAGE_IDS_INVALID", 'analysis page', issues)
    field_ids = _require_unique_ids(ledger.get("fieldInventory", []), "fieldId", "ANALYSIS_FIELD_IDS_INVALID", 'analysis field', issues) if ledger.get("fieldInventory") else set()
    logic_ids = _require_unique_ids(ledger.get("logicInventory", []), "logicId", "ANALYSIS_LOGIC_IDS_INVALID", 'analysis logic', issues)
    feature_ids = _require_unique_ids(ledger.get("featureInventory", []), "featureId", "ANALYSIS_FEATURE_IDS_INVALID", 'analysis feature', issues)
    for page in ledger.get("pageInventory", []):
        if not isinstance(page, dict):
            continue
        pid = page.get("pageId")
        for key, universe, code in [
            ("fieldIds", field_ids, "PAGE_FIELD_LINK_INVALID"),
            ("logicIds", logic_ids, "PAGE_LOGIC_LINK_INVALID"),
            ("featureIds", feature_ids, "PAGE_FEATURE_LINK_INVALID"),
        ]:
            unknown = sorted(set(unique_nonempty(page.get(key, []))) - universe)
            if unknown:
                issues.append(issue(code, "KH_Aw blocked this stage because required evidence is incomplete.", pageId=pid, field=key, unknown=unknown))
        if not nonempty(page.get("requiredRegions")) or not nonempty(page.get("states")):
            issues.append(issue("PAGE_ANALYSIS_STRUCTURE_INCOMPLETE", canonical_issue_message('PAGE_ANALYSIS_STRUCTURE_INCOMPLETE'), pageId=pid))
    minimum_findings = 1 if file_count == 0 else min(20, max(5, file_count // 100 + 5))
    if len(ledger.get("fileFindings", [])) < minimum_findings:
        issues.append(issue("ANALYSIS_FILE_FINDINGS_TOO_SHALLOW", canonical_issue_message('ANALYSIS_FILE_FINDINGS_TOO_SHALLOW'), requiredMinimum=minimum_findings, actual=len(ledger.get("fileFindings", []))))
    finding_rows = ledger.get("fileFindings", []) if isinstance(ledger.get("fileFindings"), list) else []
    finding_paths = {
        str(item.get("path"))
        for item in finding_rows
        if isinstance(item, dict) and item.get("path")
    }
    if file_count and (len(finding_rows) != file_count or finding_paths != inventory_paths):
        issues.append(issue(
            "ANALYSIS_FILE_FINDINGS_NOT_EXHAUSTIVE",
            "Exhaustive analysis requires exactly one file finding for every inventory path.",
            inventoryFileCount=file_count,
            findingCount=len(finding_rows),
            missing=sorted(inventory_paths - finding_paths)[:100],
            extra=sorted(finding_paths - inventory_paths)[:100],
        ))
    mode = state.get("analysisMode")
    if mode not in {"analysis-folder-provided", "analysis-folder-not-provided"}:
        issues.append(issue("ANALYSIS_MODE_UNRESOLVED", canonical_issue_message('ANALYSIS_MODE_UNRESOLVED')))
    if ledger.get("analysisFolderMode") != mode:
        issues.append(issue("ANALYSIS_MODE_LEDGER_MISMATCH", canonical_issue_message('ANALYSIS_MODE_LEDGER_MISMATCH')))
    if mode == "analysis-folder-provided":
        analysis_folder = Path(str(state.get("analysisFolder", "")))
        workspace_root = Path(str(state.get("workspaceRoot", "")))
        if not analysis_folder.is_dir():
            issues.append(issue("ANALYSIS_FOLDER_MISSING", canonical_issue_message('ANALYSIS_FOLDER_MISSING'), path=analysis_folder.as_posix()))
        if analysis_folder and workspace_root and is_inside(workspace_root, analysis_folder):
            issues.append(issue("OUTPUT_INSIDE_ANALYSIS_FOLDER", canonical_issue_message('OUTPUT_INSIDE_ANALYSIS_FOLDER')))
        snapshot = compare_snapshot(run_root)
        if not snapshot.get("ok"):
            issues.append(issue("ANALYSIS_FOLDER_MUTATED", canonical_issue_message('ANALYSIS_FOLDER_MUTATED'), **snapshot))
        evidence = ledger.get("analysisFolderEvidence", {})
        if evidence.get("snapshotFileCount") != snapshot.get("expectedCount") or not evidence.get("readOnlyPolicyConfirmed"):
            issues.append(issue("ANALYSIS_FOLDER_EVIDENCE_INCOMPLETE", canonical_issue_message('ANALYSIS_FOLDER_EVIDENCE_INCOMPLETE')))
    forbidden = scan_forbidden_manual_keys(ledger)
    if forbidden:
        issues.append(issue("MANUAL_DESIGN_SELECTION_FORBIDDEN", canonical_issue_message('MANUAL_DESIGN_SELECTION_FORBIDDEN'), paths=forbidden))
    _require_no_omissions(ledger, issues, 'analysis ledger')
    return issues


def _validate_source(run_root: Path, source: dict[str, Any], issues: list[dict[str, Any]]) -> bool:
    sid = str(source.get("id", ""))
    url = str(source.get("url", ""))
    stype = str(source.get("sourceType", "")).lower()
    valid = True
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        issues.append(issue("SOURCE_URL_INVALID", canonical_issue_message('SOURCE_URL_INVALID'), sourceId=sid, url=url)); valid = False
    if parsed.netloc.lower() in SEARCH_HOSTS:
        issues.append(issue("SEARCH_RESULT_IS_NOT_BODY_EVIDENCE", canonical_issue_message('SEARCH_RESULT_IS_NOT_BODY_EVIDENCE'), sourceId=sid, url=url)); valid = False
    body_path = _run_path(run_root, str(source.get("bodyPath", "")))
    text_path = _run_path(run_root, str(source.get("textPath", "")))
    if not is_inside(body_path, run_root) or not body_path.is_file() or body_path.stat().st_size < 500:
        issues.append(issue("SOURCE_BODY_MISSING_OR_TOO_SMALL", canonical_issue_message('SOURCE_BODY_MISSING_OR_TOO_SMALL'), sourceId=sid)); return False
    if source.get("bodySha256") != sha256_file(body_path):
        issues.append(issue("SOURCE_BODY_HASH_MISMATCH", canonical_issue_message('SOURCE_BODY_HASH_MISMATCH'), sourceId=sid)); valid = False
    extracted = text_path.read_text(encoding="utf-8", errors="replace") if text_path.is_file() and is_inside(text_path, run_root) else ""
    if len(extracted.strip()) < 500 or int(source.get("extractedCharacters", 0) or 0) < 500:
        issues.append(issue("SOURCE_BODY_EXTRACTION_INSUFFICIENT", canonical_issue_message('SOURCE_BODY_EXTRACTION_INSUFFICIENT'), sourceId=sid, characters=len(extracted.strip()))); valid = False
    lower = extracted[:5000].lower()
    if any(marker in lower for marker in BLOCK_PAGE_MARKERS):
        issues.append(issue("SOURCE_BLOCK_OR_LOGIN_PAGE_REJECTED", canonical_issue_message('SOURCE_BLOCK_OR_LOGIN_PAGE_REJECTED'), sourceId=sid)); valid = False
    status = int(source.get("httpStatus", 0) or 0)
    if not 200 <= status < 400:
        issues.append(issue("SOURCE_HTTP_STATUS_REJECTED", canonical_issue_message('SOURCE_HTTP_STATUS_REJECTED'), sourceId=sid, status=status)); valid = False
    if len(str(source.get("projectFitReason", "")).strip()) < 50:
        issues.append(issue("SOURCE_PROJECT_FIT_UNPROVEN", canonical_issue_message('SOURCE_PROJECT_FIT_UNPROVEN'), sourceId=sid)); valid = False
    retrieval_mode = str(source.get("retrievalMode", ""))
    if retrieval_mode == "native-browser-extraction":
        retrieval_evidence = _run_path(run_root, str(source.get("retrievalEvidencePath", "")))
        if (
            len(str(source.get("retrievalSessionId", "")).strip()) < 8
            or not retrieval_evidence.is_file()
            or source.get("retrievalEvidenceSha256") != sha256_file(retrieval_evidence)
        ):
            issues.append(issue("SOURCE_NATIVE_RETRIEVAL_EVIDENCE_INVALID", "Native browser extraction must be bound to a Codex session and physical retrieval evidence.", sourceId=sid))
            valid = False
    elif retrieval_mode != "live-fetch":
        issues.append(issue("SOURCE_RETRIEVAL_NOT_PROVEN", "A locally registered body cannot prove that its content came from the recorded URL.", sourceId=sid, retrievalMode=retrieval_mode))
        valid = False
    fetched_at = str(source.get("fetchedAt", ""))
    try:
        fetched_time = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - fetched_time.astimezone(timezone.utc)).days
    except (TypeError, ValueError):
        age_days = 10**9
    if age_days < 0 or age_days > 180:
        issues.append(issue("SOURCE_FRESHNESS_UNPROVEN", "Research evidence must include a valid retrieval date within the last 180 days.", sourceId=sid, fetchedAt=fetched_at))
        valid = False
    if stype not in {"web", "github", "official"}:
        issues.append(issue("SOURCE_TYPE_INVALID", canonical_issue_message('SOURCE_TYPE_INVALID'), sourceId=sid, sourceType=stype)); valid = False
    return valid


def gate_research(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    requirements = _read_required_json(run_root / "contract" / "requirements.json", issues, "REQUIREMENTS_MISSING") or {}
    plan = _read_required_json(run_root / "evidence" / "research-plan.json", issues, "RESEARCH_PLAN_MISSING") or {}
    registry = _read_required_json(run_root / "evidence" / "source-registry.json", issues, "SOURCE_REGISTRY_MISSING") or {}
    forbidden = scan_forbidden_manual_keys(plan)
    if forbidden:
        issues.append(issue("MANUAL_DESIGN_SELECTION_FORBIDDEN", canonical_issue_message('MANUAL_DESIGN_SELECTION_FORBIDDEN'), paths=forbidden))
    elements = plan.get("elements", []) if isinstance(plan, dict) else []
    element_ids = _require_unique_ids(elements, "id", "RESEARCH_ELEMENT_IDS_INVALID", 'research element', issues)
    categories = {str(item.get("category", "")) for item in elements if isinstance(item, dict)}
    missing_categories = [category for category in RESEARCH_CATEGORIES if category not in categories]
    if missing_categories:
        issues.append(issue("RESEARCH_CATEGORY_COVERAGE_INCOMPLETE", canonical_issue_message('RESEARCH_CATEGORY_COVERAGE_INCOMPLETE'), missing=missing_categories))
    requirement_ids = {item.get("id") for item in requirements.get("requirements", []) if isinstance(item, dict)}
    linked_ids = {rid for element in elements if isinstance(element, dict) for rid in element.get("requirementIds", [])}
    missing_links = sorted(rid for rid in requirement_ids if rid and rid not in linked_ids)
    if missing_links:
        issues.append(issue("RESEARCH_REQUIREMENT_LINKS_INCOMPLETE", canonical_issue_message('RESEARCH_REQUIREMENT_LINKS_INCOMPLETE'), missing=missing_links))
    for element in elements:
        if not isinstance(element, dict):
            continue
        eid = str(element.get("id", ""))
        if element.get("status") == "AI_MUST_REPLACE_DYNAMICALLY" or "AI_MUST_REPLACE_DYNAMICALLY" in str(element.get("label", "")):
            issues.append(issue("RESEARCH_PLAN_PLACEHOLDER_REMAINS", canonical_issue_message('RESEARCH_PLAN_PLACEHOLDER_REMAINS'), elementId=eid))
        if len(unique_nonempty(element.get("webQueries", []))) < 2:
            issues.append(issue("WEB_QUERY_MINIMUM_NOT_MET", canonical_issue_message('WEB_QUERY_MINIMUM_NOT_MET'), elementId=eid))
        if len(unique_nonempty(element.get("githubQueries", []))) < 2:
            issues.append(issue("GITHUB_QUERY_MINIMUM_NOT_MET", canonical_issue_message('GITHUB_QUERY_MINIMUM_NOT_MET'), elementId=eid))
        if len(str(element.get("reason", ""))) < 30:
            issues.append(issue("RESEARCH_ELEMENT_REASON_INSUFFICIENT", canonical_issue_message('RESEARCH_ELEMENT_REASON_INSUFFICIENT'), elementId=eid))
    sources = registry.get("sources", []) if isinstance(registry, dict) else []
    _require_unique_ids(sources, "id", "SOURCE_IDS_INVALID", 'source', issues)
    seen_pairs: set[tuple[str, str]] = set()
    valid_by_element: dict[str, dict[str, list[str]]] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        eid = str(source.get("elementId", ""))
        url = str(source.get("url", ""))
        if eid not in element_ids:
            issues.append(issue("SOURCE_ELEMENT_LINK_INVALID", canonical_issue_message('SOURCE_ELEMENT_LINK_INVALID'), sourceId=source.get("id"), elementId=eid))
        pair = (eid, url)
        if pair in seen_pairs:
            issues.append(issue("DUPLICATE_RESEARCH_SOURCE", canonical_issue_message('DUPLICATE_RESEARCH_SOURCE'), elementId=eid, url=url))
        seen_pairs.add(pair)
        if _validate_source(run_root, source, issues):
            source_type = str(source.get("sourceType", "")).lower()
            bucket = "github" if source_type == "github" else "web"
            buckets = valid_by_element.setdefault(eid, {"web": [], "github": [], "official": []})
            buckets[bucket].append(url)
            if source_type == "official":
                buckets["official"].append(url)
    for element in elements:
        if not isinstance(element, dict):
            continue
        eid = str(element.get("id", ""))
        required = 1 if element.get("exceptionCode") == "KOREA_ADDRESS_DAUM_POSTCODE" else 2
        buckets = valid_by_element.get(eid, {"web": [], "github": [], "official": []})
        web_count = len(set(buckets["web"]))
        gh_count = len(set(buckets["github"]))
        if element.get("category") == "platform" and not buckets["official"]:
            issues.append(issue(
                "OFFICIAL_PLATFORM_SOURCE_MISSING",
                "Platform and core technology research must include current official documentation.",
                elementId=eid,
            ))
        if web_count < required or gh_count < required:
            issues.append(issue("BODY_BACKED_SOURCE_MINIMUM_NOT_MET", canonical_issue_message('BODY_BACKED_SOURCE_MINIMUM_NOT_MET'), elementId=eid, required=required, web=web_count, github=gh_count))
    _require_no_omissions(plan, issues, 'research plan')
    return issues


def gate_design(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    analysis = _read_required_json(run_root / "analysis" / "analysis-ledger.json", issues, "ANALYSIS_LEDGER_MISSING") or {}
    inventory = _read_required_json(run_root / "design" / "page-inventory.json", issues, "PAGE_INVENTORY_MISSING") or {}
    ledger = _read_required_json(run_root / "design" / "design-ledger.json", issues, "DESIGN_LEDGER_MISSING") or {}
    registry = _read_required_json(run_root / "evidence" / "source-registry.json", issues, "SOURCE_REGISTRY_MISSING") or {}
    forbidden = scan_forbidden_manual_keys(ledger)
    if forbidden:
        issues.append(issue("MANUAL_DESIGN_SELECTION_FORBIDDEN", canonical_issue_message('MANUAL_DESIGN_SELECTION_FORBIDDEN'), paths=forbidden))
    origin = ledger.get("designOriginPolicy", {}) if isinstance(ledger, dict) else {}
    if origin.get("mode") not in {"dynamic-web-body-research", "dynamic-web-body-research-plus-existing-brand"}:
        issues.append(issue("DYNAMIC_DESIGN_ORIGIN_REQUIRED", canonical_issue_message('DYNAMIC_DESIGN_ORIGIN_REQUIRED')))
    if origin.get("manualConceptSelection") is not False or origin.get("manualColorSelection") is not False or origin.get("fixedDesignPreset") is not False or origin.get("projectSpecificEveryRun") is not True:
        issues.append(issue("MANUAL_OR_FIXED_DESIGN_POLICY_REJECTED", canonical_issue_message('MANUAL_OR_FIXED_DESIGN_POLICY_REJECTED')))
    analysis_pages = analysis.get("pageInventory", []) if isinstance(analysis, dict) else []
    pages = inventory.get("pages", []) if isinstance(inventory, dict) else []
    designs = ledger.get("pages", []) if isinstance(ledger, dict) else []
    _gate_dynamic_page_inventory(run_root, inventory, issues)
    analysis_ids = _require_unique_ids(analysis_pages, "pageId", "ANALYSIS_PAGE_IDS_INVALID", 'analysis page', issues)
    page_ids = _require_unique_ids(pages, "pageId", "PAGE_IDS_INVALID", 'design page', issues)
    design_ids = _require_unique_ids(designs, "pageId", "DESIGN_PAGE_IDS_INVALID", 'page design', issues)
    if page_ids != analysis_ids:
        issues.append(issue("PAGE_INVENTORY_ANALYSIS_MISMATCH", canonical_issue_message('PAGE_INVENTORY_ANALYSIS_MISMATCH'), analysis=sorted(analysis_ids), designInventory=sorted(page_ids)))
    if design_ids != page_ids or len(designs) != len(page_ids):
        issues.append(issue("FULL_PAGE_MOCKUP_ONE_TO_ONE_REQUIRED", canonical_issue_message('FULL_PAGE_MOCKUP_ONE_TO_ONE_REQUIRED'), expected=sorted(page_ids), actual=sorted(design_ids)))
    source_by_id = {str(item.get("id")): item for item in registry.get("sources", []) if isinstance(item, dict)}
    inventory_by_id = {str(item.get("pageId")): item for item in pages if isinstance(item, dict)}
    mockup_paths: list[str] = []
    screenshot_paths: list[str] = []
    for page in designs:
        if not isinstance(page, dict):
            continue
        pid = str(page.get("pageId", ""))
        page_spec = inventory_by_id.get(pid, {})
        mockup = str(page.get("mockupPath", ""))
        screenshot = str(page.get("screenshotPath", ""))
        mockup_paths.append(mockup)
        screenshot_paths.append(screenshot)
        if not _file_ok(run_root, mockup, 800):
            issues.append(issue("PAGE_MOCKUP_FILE_MISSING", canonical_issue_message('PAGE_MOCKUP_FILE_MISSING'), pageId=pid, path=mockup))
            text = ""
        else:
            text = _run_path(run_root, mockup).read_text(encoding="utf-8", errors="replace")
            if pid and pid not in text:
                issues.append(issue("PAGE_MOCKUP_ID_MARKER_MISSING", canonical_issue_message('PAGE_MOCKUP_ID_MARKER_MISSING'), pageId=pid, path=mockup))
            if len(re.findall(r"<(?:header|main|section|article|nav|form|footer|div)\b", text, re.I)) < 5:
                issues.append(issue("PAGE_MOCKUP_VISUAL_STRUCTURE_TOO_SHALLOW", canonical_issue_message('PAGE_MOCKUP_VISUAL_STRUCTURE_TOO_SHALLOW'), pageId=pid))
        screenshot_file = _run_path(run_root, screenshot)
        png = _png_info(screenshot_file) if screenshot_file.is_file() else None
        if not png or png[0] < 320 or png[1] < 568 or screenshot_file.stat().st_size < 1000:
            issues.append(issue("PAGE_MOCKUP_SCREENSHOT_INVALID", canonical_issue_message('PAGE_MOCKUP_SCREENSHOT_INVALID'), pageId=pid, path=screenshot, dimensions=png))
        else:
            if page.get("screenshotSha256") != sha256_file(screenshot_file):
                issues.append(issue("PAGE_MOCKUP_SCREENSHOT_HASH_MISMATCH", canonical_issue_message('PAGE_MOCKUP_SCREENSHOT_HASH_MISMATCH'), pageId=pid))
        mockup_file = _run_path(run_root, mockup)
        if mockup_file.is_file() and page.get("mockupSha256") != sha256_file(mockup_file):
            issues.append(issue("PAGE_MOCKUP_FILE_HASH_MISMATCH", canonical_issue_message('PAGE_MOCKUP_FILE_HASH_MISMATCH'), pageId=pid))
        research_ids = unique_nonempty(page.get("researchSourceIds", []))
        research_types = {str(source_by_id.get(value, {}).get("sourceType", "")) for value in research_ids if value in source_by_id}
        if len(research_ids) < 4 or any(value not in source_by_id for value in research_ids) or "github" not in research_types or not research_types.intersection({"web", "official"}):
            issues.append(issue("DESIGN_RESEARCH_TRACE_INSUFFICIENT", canonical_issue_message('DESIGN_RESEARCH_TRACE_INSUFFICIENT'), pageId=pid, sourceIds=research_ids))
        for field in ["layoutRationale", "visualHierarchy", "typographyStrategy", "colorStrategy", "smallBusinessAttentionStrategy", "conversionStrategy", "accessibilityStrategy"]:
            if len(str(page.get(field, "")).strip()) < 40:
                issues.append(issue("PAGE_DESIGN_FIELD_INSUFFICIENT", canonical_issue_message('PAGE_DESIGN_FIELD_INSUFFICIENT'), pageId=pid, field=field))
        expected_regions = set(unique_nonempty(page_spec.get("requiredRegions", [])))
        designed_regions = set(unique_nonempty(page.get("regionIds", [])))
        if designed_regions != expected_regions:
            issues.append(issue("PAGE_REGION_COVERAGE_INCOMPLETE", canonical_issue_message('PAGE_REGION_COVERAGE_INCOMPLETE'), pageId=pid, expected=sorted(expected_regions), actual=sorted(designed_regions)))
        for region in expected_regions:
            if text and region not in text:
                issues.append(issue("MOCKUP_REGION_MARKER_MISSING", canonical_issue_message('MOCKUP_REGION_MARKER_MISSING'), pageId=pid, regionId=region))
        for key, code in [("fieldIds", "PAGE_FIELD_DESIGN_COVERAGE_INCOMPLETE"), ("logicIds", "PAGE_LOGIC_DESIGN_COVERAGE_INCOMPLETE"), ("featureIds", "PAGE_FEATURE_DESIGN_COVERAGE_INCOMPLETE")]:
            expected_values = set(unique_nonempty(page_spec.get(key, [])))
            actual_values = set(unique_nonempty(page.get(key, [])))
            if actual_values != expected_values:
                issues.append(issue(code, "KH_Aw blocked this stage because required evidence is incomplete.", pageId=pid, field=key, expected=sorted(expected_values), actual=sorted(actual_values)))
            missing_markers = [value for value in expected_values if text and value not in text]
            if missing_markers:
                issues.append(issue(f"{code}_MOCKUP_MARKER_MISSING", "KH_Aw blocked this stage because required evidence is incomplete.", pageId=pid, field=key, missing=missing_markers))
        expected_states = set(unique_nonempty(page_spec.get("states", [])))
        actual_states = {str(item.get("name", item)) if isinstance(item, dict) else str(item) for item in page.get("states", [])}
        if not expected_states.issubset(actual_states) or "default" not in actual_states:
            issues.append(issue("PAGE_STATE_DESIGN_COVERAGE_INCOMPLETE", canonical_issue_message('PAGE_STATE_DESIGN_COVERAGE_INCOMPLETE'), pageId=pid, expected=sorted(expected_states), actual=sorted(actual_states)))
        image_strategy = page.get("imageStrategy", {})
        motion_strategy = page.get("motionStrategy", {})
        hero_strategy = page.get("heroStrategy", {})
        visibility = str(page_spec.get("visibility", "public")).lower()
        route_or_entry = str(page_spec.get("routeOrEntry", "")).strip().lower()
        primary_entry = page_spec.get("primaryEntry") is True or route_or_entry in {"/", "index", "index.html", "home"}
        if not isinstance(hero_strategy, dict) or "required" not in hero_strategy or len(str(hero_strategy.get("reason", "")).strip()) < 30:
            issues.append(issue("HERO_DECISION_MISSING", "Every page design must record a project-specific hero or first-viewport decision.", pageId=pid))
        elif primary_entry and visibility in PUBLIC_VISIBILITIES and hero_strategy.get("required") is not True:
            issues.append(issue("PRIMARY_ENTRY_HERO_REQUIRED", "A public primary entry page must provide a strong first-viewport hero signal.", pageId=pid, routeOrEntry=route_or_entry))
        elif hero_strategy.get("required") is True:
            for field in ["type", "headlinePurpose", "visualAssetSlotId", "firstViewportSignal", "nextSectionHint"]:
                if not nonempty(hero_strategy.get(field)):
                    issues.append(issue("HERO_STRATEGY_INCOMPLETE", "Required hero strategy fields are missing.", pageId=pid, field=field))
        if not isinstance(image_strategy, dict) or "required" not in image_strategy or len(str(image_strategy.get("reason", ""))) < 30:
            issues.append(issue("IMAGE_DECISION_MISSING", canonical_issue_message('IMAGE_DECISION_MISSING'), pageId=pid))
        elif visibility in PUBLIC_VISIBILITIES and image_strategy.get("required") is not True:
            exception = str(image_strategy.get("engagementException", ""))
            if len(exception) < 60:
                issues.append(issue("PUBLIC_PAGE_IMAGE_REQUIRED", canonical_issue_message('PUBLIC_PAGE_IMAGE_REQUIRED'), pageId=pid, visibility=visibility))
        elif image_strategy.get("required") and not image_strategy.get("slots"):
            issues.append(issue("IMAGE_SLOT_PLAN_MISSING", canonical_issue_message('IMAGE_SLOT_PLAN_MISSING'), pageId=pid))
        elif image_strategy.get("required"):
            for slot in image_strategy.get("slots", []):
                if not isinstance(slot, dict) or not all(nonempty(slot.get(field)) for field in ["slotId", "purpose", "aspectRatio", "sourceStrategy"]):
                    issues.append(issue("IMAGE_SLOT_PLAN_INCOMPLETE", canonical_issue_message('IMAGE_SLOT_PLAN_INCOMPLETE'), pageId=pid, slot=slot))
        if not isinstance(motion_strategy, dict) or "required" not in motion_strategy or len(str(motion_strategy.get("reason", ""))) < 30:
            issues.append(issue("MOTION_DECISION_MISSING", canonical_issue_message('MOTION_DECISION_MISSING'), pageId=pid))
        elif visibility not in STATIC_EXCEPTION_VISIBILITIES and motion_strategy.get("required") is not True:
            exception = str(motion_strategy.get("engagementException", ""))
            if len(exception) < 60:
                issues.append(issue("USER_PAGE_MOTION_REQUIRED", canonical_issue_message('USER_PAGE_MOTION_REQUIRED'), pageId=pid, visibility=visibility))
        elif motion_strategy.get("required") and (not motion_strategy.get("motions") or len(str(motion_strategy.get("reducedMotionPlan", ""))) < 20):
            issues.append(issue("MOTION_STORYBOARD_MISSING", canonical_issue_message('MOTION_STORYBOARD_MISSING'), pageId=pid))
        elif motion_strategy.get("required"):
            for motion in motion_strategy.get("motions", []):
                if not isinstance(motion, dict) or not all(nonempty(motion.get(field)) for field in ["motionId", "trigger", "from", "to", "duration", "easing", "purpose"]):
                    issues.append(issue("MOTION_STORYBOARD_INCOMPLETE", canonical_issue_message('MOTION_STORYBOARD_INCOMPLETE'), pageId=pid, motion=motion))
    if len(mockup_paths) != len(set(mockup_paths)) or len(screenshot_paths) != len(set(screenshot_paths)) or any(not value for value in mockup_paths + screenshot_paths):
        issues.append(issue("REPRESENTATIVE_SAMPLE_REUSE_FORBIDDEN", canonical_issue_message('REPRESENTATIVE_SAMPLE_REUSE_FORBIDDEN')))
    board = ledger.get("visualStructureBoard", {})
    board_image = _run_path(run_root, str(board.get("imagePath", "")))
    board_html = _run_path(run_root, str(board.get("htmlPath", "")))
    if not _file_ok(run_root, str(board.get("htmlPath", "")), 800) or not _png_info(board_image) or board_image.stat().st_size < 1000:
        issues.append(issue("VISUAL_STRUCTURE_BOARD_MISSING", canonical_issue_message('VISUAL_STRUCTURE_BOARD_MISSING')))
    else:
        if board.get("htmlSha256") != sha256_file(board_html) or board.get("imageSha256") != sha256_file(board_image):
            issues.append(issue("VISUAL_STRUCTURE_BOARD_HASH_MISMATCH", canonical_issue_message('VISUAL_STRUCTURE_BOARD_HASH_MISMATCH')))
    if set(unique_nonempty(board.get("pageIds", []))) != page_ids:
        issues.append(issue("VISUAL_BOARD_PAGE_COVERAGE_INCOMPLETE", canonical_issue_message('VISUAL_BOARD_PAGE_COVERAGE_INCOMPLETE')))
    for field in ["smallBusinessAttentionStrategy", "imageSystem", "heroSystem", "iconSystem", "fontSystem", "motionSystem", "accessibilitySystem", "conversionSystem", "performanceBudget"]:
        if not nonempty(ledger.get("globalQuality", {}).get(field)):
            issues.append(issue("GLOBAL_DESIGN_QUALITY_FIELD_MISSING", canonical_issue_message('GLOBAL_DESIGN_QUALITY_FIELD_MISSING'), field=field))
    _require_no_omissions(inventory, issues, 'page inventory')
    _require_no_omissions(ledger, issues, 'design ledger')
    return issues


def gate_implement(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    issues.extend(_gate_copy_audit(run_root, state))
    issues.extend(_gate_target_artifact_shape(run_root, state))
    pages = (_read_required_json(run_root / "design" / "page-inventory.json", issues, "PAGE_INVENTORY_MISSING") or {}).get("pages", [])
    design_pages = (_read_required_json(run_root / "design" / "design-ledger.json", issues, "DESIGN_LEDGER_MISSING") or {}).get("pages", [])
    ledger = _read_required_json(run_root / "implementation" / "implementation-ledger.json", issues, "IMPLEMENTATION_LEDGER_MISSING") or {}
    forbidden = scan_forbidden_manual_keys(ledger)
    if forbidden:
        issues.append(issue("MANUAL_DESIGN_SELECTION_FORBIDDEN", canonical_issue_message('MANUAL_DESIGN_SELECTION_FORBIDDEN'), paths=forbidden))
    impl_pages = ledger.get("pages", []) if isinstance(ledger, dict) else []
    expected = _require_unique_ids(pages, "pageId", "PAGE_IDS_INVALID", 'page', issues)
    actual = _require_unique_ids(impl_pages, "pageId", "IMPLEMENTATION_PAGE_IDS_INVALID", 'implementation page', issues)
    if expected != actual or len(impl_pages) != len(expected):
        issues.append(issue("IMPLEMENTATION_PAGE_COVERAGE_INCOMPLETE", canonical_issue_message('IMPLEMENTATION_PAGE_COVERAGE_INCOMPLETE'), expected=sorted(expected), actual=sorted(actual)))
    project_root = Path(str(state.get("projectRoot", "")))
    design_by_id = {str(item.get("pageId", "")): item for item in design_pages if isinstance(item, dict)}
    page_by_id = {str(item.get("pageId", "")): item for item in pages if isinstance(item, dict)}
    image_assets = {str(item.get("imageId", "")): item for item in ledger.get("imageAssets", []) if isinstance(item, dict)}
    motions = {str(item.get("motionId", "")): item for item in ledger.get("motionImplementations", []) if isinstance(item, dict)}
    _require_unique_ids(list(image_assets.values()), "imageId", "IMAGE_IDS_INVALID", 'image', issues) if image_assets else None
    _require_unique_ids(list(motions.values()), "motionId", "MOTION_IDS_INVALID", 'motion', issues) if motions else None
    for page in impl_pages:
        if not isinstance(page, dict):
            continue
        pid = str(page.get("pageId", ""))
        files = [safe_resolve(value, project_root) for value in page.get("targetFiles", []) if str(value).strip()]
        if not files or any(not file.is_file() or not is_inside(file, project_root) for file in files):
            issues.append(issue("IMPLEMENTATION_TARGET_FILES_MISSING", canonical_issue_message('IMPLEMENTATION_TARGET_FILES_MISSING'), pageId=pid, files=[f.as_posix() for f in files]))
        hashes = page.get("fileHashes", {})
        combined_text = ""
        for file in files:
            if not file.is_file() or not is_inside(file, project_root):
                continue
            rel = file.relative_to(project_root).as_posix()
            if hashes.get(rel) != sha256_file(file):
                issues.append(issue("IMPLEMENTATION_FILE_HASH_MISSING", canonical_issue_message('IMPLEMENTATION_FILE_HASH_MISSING'), pageId=pid, file=rel))
            if file.suffix.lower() in {".html", ".css", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".kt", ".java", ".xml", ".py", ".dart", ".vue", ".svelte"}:
                combined_text += "\n" + file.read_text(encoding="utf-8", errors="replace")
        if korean_ui_character_count(files) < 2:
            issues.append(issue(
                "KOREAN_USER_INTERFACE_EVIDENCE_MISSING",
                "Every implemented user-facing page must contain physical Korean UI text.",
                pageId=pid,
                targetFiles=[file.as_posix() for file in files],
            ))
        spec = page_by_id.get(pid, {})
        design = design_by_id.get(pid, {})
        for ledger_key, spec_key, code in [
            ("implementedRegionIds", "requiredRegions", "IMPLEMENTED_REGIONS_INCOMPLETE"),
            ("implementedFieldIds", "fieldIds", "IMPLEMENTED_FIELDS_INCOMPLETE"),
            ("implementedLogicIds", "logicIds", "IMPLEMENTED_LOGIC_INCOMPLETE"),
            ("implementedFeatureIds", "featureIds", "IMPLEMENTED_FEATURES_INCOMPLETE"),
        ]:
            expected_ids = set(unique_nonempty(spec.get(spec_key, [])))
            actual_ids = set(unique_nonempty(page.get(ledger_key, [])))
            if expected_ids != actual_ids:
                issues.append(issue(code, "KH_Aw blocked this stage because required evidence is incomplete.", pageId=pid, expected=sorted(expected_ids), actual=sorted(actual_ids)))
            missing_markers = [value for value in expected_ids if not _marker_has_executable_context(combined_text, value)]
            if missing_markers:
                issues.append(issue(f"{code}_CODE_MARKER_MISSING", "KH_Aw blocked this stage because required evidence is incomplete.", pageId=pid, missing=missing_markers))
        image_ids = set(unique_nonempty(page.get("imageAssetIds", [])))
        motion_ids = set(unique_nonempty(page.get("motionIds", [])))
        if design.get("imageStrategy", {}).get("required") and not image_ids:
            issues.append(issue("PLANNED_IMAGES_NOT_BOUND", canonical_issue_message('PLANNED_IMAGES_NOT_BOUND'), pageId=pid))
        if design.get("motionStrategy", {}).get("required") and not motion_ids:
            issues.append(issue("PLANNED_MOTION_NOT_IMPLEMENTED", canonical_issue_message('PLANNED_MOTION_NOT_IMPLEMENTED'), pageId=pid))
        if design.get("heroStrategy", {}).get("required") is True:
            hero_marker = str(page.get("heroMarker", "")).strip()
            if not hero_marker or not _marker_has_executable_context(combined_text, hero_marker):
                issues.append(issue(
                    "HERO_IMPLEMENTATION_MISSING",
                    "A required hero must have a physical implementation marker in executable or markup code.",
                    pageId=pid,
                    heroMarker=hero_marker,
                ))
        unknown_images = sorted(image_ids - set(image_assets))
        unknown_motions = sorted(motion_ids - set(motions))
        if unknown_images:
            issues.append(issue("PAGE_IMAGE_LINK_INVALID", canonical_issue_message('PAGE_IMAGE_LINK_INVALID'), pageId=pid, unknown=unknown_images))
        if unknown_motions:
            issues.append(issue("PAGE_MOTION_LINK_INVALID", canonical_issue_message('PAGE_MOTION_LINK_INVALID'), pageId=pid, unknown=unknown_motions))
    for image_id, asset in image_assets.items():
        path = safe_resolve(asset.get("assetPath", ""), project_root)
        if not path.is_file() or not is_inside(path, project_root) or path.stat().st_size < 500:
            issues.append(issue("IMAGE_ASSET_MISSING", canonical_issue_message('IMAGE_ASSET_MISSING'), imageId=image_id, path=path.as_posix()))
            continue
        if asset.get("sha256") != sha256_file(path):
            issues.append(issue("IMAGE_ASSET_HASH_MISMATCH", canonical_issue_message('IMAGE_ASSET_HASH_MISMATCH'), imageId=image_id))
        if len(str(asset.get("sourceOrPrompt", ""))) < 20 or len(str(asset.get("licenseOrOwnership", ""))) < 10 or len(str(asset.get("projectFitReason", ""))) < 30:
            issues.append(issue("IMAGE_PROVENANCE_MISSING", canonical_issue_message('IMAGE_PROVENANCE_MISSING'), imageId=image_id))
        usages = unique_nonempty(asset.get("usageLocations", []))
        if not usages:
            issues.append(issue("IMAGE_USAGE_LOCATION_MISSING", canonical_issue_message('IMAGE_USAGE_LOCATION_MISSING'), imageId=image_id))
        else:
            rel_asset = path.relative_to(project_root).as_posix()
            for usage in usages:
                usage_file = safe_resolve(usage, project_root)
                text = usage_file.read_text(encoding="utf-8", errors="replace") if usage_file.is_file() else ""
                if rel_asset not in text and path.name not in text:
                    issues.append(issue("IMAGE_NOT_REFERENCED_BY_CODE", canonical_issue_message('IMAGE_NOT_REFERENCED_BY_CODE'), imageId=image_id, usage=usage))
    for motion_id, motion in motions.items():
        file = safe_resolve(motion.get("targetFile", ""), project_root)
        text = file.read_text(encoding="utf-8", errors="replace") if file.is_file() and is_inside(file, project_root) else ""
        marker = str(motion.get("implementationMarker", ""))
        reduced = str(motion.get("reducedMotionMarker", ""))
        if not _marker_has_executable_context(text, marker):
            issues.append(issue("MOTION_CODE_MARKER_MISSING", canonical_issue_message('MOTION_CODE_MARKER_MISSING'), motionId=motion_id, file=file.as_posix()))
        if not reduced or reduced not in text:
            issues.append(issue("REDUCED_MOTION_CODE_MISSING", canonical_issue_message('REDUCED_MOTION_CODE_MISSING'), motionId=motion_id, file=file.as_posix()))
        for field in ["trigger", "purpose", "duration", "easing"]:
            if not nonempty(motion.get(field)):
                issues.append(issue("MOTION_SPEC_INCOMPLETE", canonical_issue_message('MOTION_SPEC_INCOMPLETE'), motionId=motion_id, field=field))
    blocking = [item for item in ledger.get("unresolvedIssues", []) if isinstance(item, dict) and item.get("severity") in {"critical", "major"} and item.get("status") != "resolved"]
    if blocking:
        issues.append(issue("BLOCKING_IMPLEMENTATION_ISSUES_REMAIN", canonical_issue_message('BLOCKING_IMPLEMENTATION_ISSUES_REMAIN'), count=len(blocking)))
    test_items = ledger.get("tests", [])
    if not test_items:
        issues.append(issue("IMPLEMENTATION_TEST_MAP_MISSING", canonical_issue_message('IMPLEMENTATION_TEST_MAP_MISSING')))
    else:
        _require_unique_ids(test_items, "testId", "IMPLEMENTATION_TEST_IDS_INVALID", 'implementation test', issues)
        all_trace_ids = set()
        for spec in pages:
            if not isinstance(spec, dict):
                continue
            all_trace_ids.add(str(spec.get("pageId", "")))
            for key in ["requiredRegions", "fieldIds", "logicIds", "featureIds"]:
                all_trace_ids.update(unique_nonempty(spec.get(key, [])))
        covered_ids: set[str] = set()
        for test in test_items:
            if not isinstance(test, dict):
                continue
            test_id = str(test.get("testId", ""))
            test_file = safe_resolve(test.get("testFile", ""), project_root)
            if not test_file.is_file() or not is_inside(test_file, project_root):
                issues.append(issue("IMPLEMENTATION_TEST_FILE_MISSING", canonical_issue_message('IMPLEMENTATION_TEST_FILE_MISSING'), testId=test_id, file=test_file.as_posix()))
                continue
            if test.get("sha256") != sha256_file(test_file):
                issues.append(issue("IMPLEMENTATION_TEST_FILE_HASH_MISMATCH", canonical_issue_message('IMPLEMENTATION_TEST_FILE_HASH_MISMATCH'), testId=test_id))
            marker = str(test.get("testMarker", ""))
            text = test_file.read_text(encoding="utf-8", errors="replace")
            if not _marker_has_executable_context(text, marker):
                issues.append(issue("IMPLEMENTATION_TEST_MARKER_MISSING", canonical_issue_message('IMPLEMENTATION_TEST_MARKER_MISSING'), testId=test_id, marker=marker))
            target_ids = set(unique_nonempty(test.get("targetIds", [])))
            if not target_ids or not target_ids.issubset(all_trace_ids):
                issues.append(issue("IMPLEMENTATION_TEST_TARGET_INVALID", canonical_issue_message('IMPLEMENTATION_TEST_TARGET_INVALID'), testId=test_id, targets=sorted(target_ids)))
            covered_ids.update(target_ids)
        missing_test_coverage = sorted(value for value in all_trace_ids if value and value not in covered_ids)
        if missing_test_coverage:
            issues.append(issue("IMPLEMENTATION_TEST_COVERAGE_INCOMPLETE", canonical_issue_message('IMPLEMENTATION_TEST_COVERAGE_INCOMPLETE'), missing=missing_test_coverage))
    _require_no_omissions(ledger, issues, 'implementation ledger')
    return issues


def gate_review(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    pages = (_read_required_json(run_root / "design" / "page-inventory.json", issues, "PAGE_INVENTORY_MISSING") or {}).get("pages", [])
    review = _read_required_json(run_root / "review" / "review.json", issues, "REVIEW_MISSING") or {}
    expected = _require_unique_ids(pages, "pageId", "PAGE_IDS_INVALID", 'page', issues)
    reviewed = review.get("pages", []) if isinstance(review, dict) else []
    actual = _require_unique_ids(reviewed, "pageId", "REVIEW_PAGE_IDS_INVALID", 'review page', issues)
    if expected != actual or len(reviewed) != len(expected):
        issues.append(issue("REVIEW_PAGE_COVERAGE_INCOMPLETE", canonical_issue_message('REVIEW_PAGE_COVERAGE_INCOMPLETE'), expected=sorted(expected), actual=sorted(actual)))
    required_checks = [
        "structureMatched", "fieldsMatched", "logicMatched", "featuresMatched",
        "imagesMatched", "heroMatched", "motionMatched", "typographyMatched",
        "colorMatched", "iconMatched", "koreanUiMatched", "statesMatched",
        "overlapFree", "responsivePass", "accessibilityPass",
    ]
    test_report = read_json(run_root / "test" / "test-report.json", {})
    execution_map = {str(item.get("executionId")): item for item in test_report.get("toolExecutions", []) if isinstance(item, dict)}
    implement_gate_path = run_root / "reports" / "gate-implement.json"
    implement_gate = read_json(implement_gate_path, {})
    if implement_gate.get("pass") is not True:
        issues.append(issue("IMPLEMENTATION_GATE_EVIDENCE_MISSING", canonical_issue_message('IMPLEMENTATION_GATE_EVIDENCE_MISSING')))
    for item in reviewed:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("pageId", ""))
        screenshot = _run_path(run_root, str(item.get("actualScreenshotPath", "")))
        dimensions = _png_info(screenshot) if screenshot.is_file() else None
        if not dimensions or dimensions[0] < 320 or dimensions[1] < 568 or screenshot.stat().st_size < 1000:
            issues.append(issue("ACTUAL_SCREENSHOT_INVALID", canonical_issue_message('ACTUAL_SCREENSHOT_INVALID'), pageId=pid, dimensions=dimensions))
        elif item.get("actualScreenshotSha256") != sha256_file(screenshot):
            issues.append(issue("ACTUAL_SCREENSHOT_HASH_MISMATCH", canonical_issue_message('ACTUAL_SCREENSHOT_HASH_MISMATCH'), pageId=pid))
        if not _file_ok(run_root, str(item.get("mockupPath", "")), 800):
            issues.append(issue("REVIEW_MOCKUP_LINK_MISSING", canonical_issue_message('REVIEW_MOCKUP_LINK_MISSING'), pageId=pid))
        evidence_path = _run_path(run_root, str(item.get("evidencePath", "")))
        if not evidence_path.is_file() or item.get("evidenceSha256") != sha256_file(evidence_path):
            issues.append(issue("REVIEW_RUNTIME_EVIDENCE_INVALID", canonical_issue_message('REVIEW_RUNTIME_EVIDENCE_INVALID'), pageId=pid))
        else:
            evidence_text = evidence_path.read_text(encoding="utf-8", errors="replace")
            if screenshot.is_file() and screenshot.as_posix() not in evidence_text and screenshot.relative_to(run_root).as_posix() not in evidence_text:
                issues.append(issue("REVIEW_SCREENSHOT_NOT_BOUND_TO_RUNTIME", canonical_issue_message('REVIEW_SCREENSHOT_NOT_BOUND_TO_RUNTIME'), pageId=pid))
        linked_execs = set(unique_nonempty(item.get("toolExecutionIds", [])))
        if not linked_execs or any(execution_map.get(value, {}).get("exitCode") != 0 for value in linked_execs):
            issues.append(issue("REVIEW_TOOL_EXECUTION_LINK_INVALID", canonical_issue_message('REVIEW_TOOL_EXECUTION_LINK_INVALID'), pageId=pid, executionIds=sorted(linked_execs)))
        if item.get("implementationGatePath") != "reports/gate-implement.json" or item.get("implementationGateSha256") != (sha256_file(implement_gate_path) if implement_gate_path.is_file() else ""):
            issues.append(issue("REVIEW_IMPLEMENTATION_GATE_HASH_INVALID", canonical_issue_message('REVIEW_IMPLEMENTATION_GATE_HASH_INVALID'), pageId=pid))
        failed = [field for field in required_checks if item.get(field) is not True]
        if failed or item.get("pass") is not True:
            issues.append(issue("PAGE_REVIEW_FAILED", canonical_issue_message('PAGE_REVIEW_FAILED'), pageId=pid, failed=failed))
        if item.get("issues"):
            open_items = [value for value in item.get("issues", []) if not isinstance(value, dict) or value.get("status") != "resolved"]
            if open_items:
                issues.append(issue("PAGE_REVIEW_ISSUES_OPEN", canonical_issue_message('PAGE_REVIEW_ISSUES_OPEN'), pageId=pid, count=len(open_items)))
    if not review.get("crossPageConsistency"):
        issues.append(issue("CROSS_PAGE_CONSISTENCY_REVIEW_MISSING", canonical_issue_message('CROSS_PAGE_CONSISTENCY_REVIEW_MISSING')))
    else:
        for item in review.get("crossPageConsistency", []):
            if not isinstance(item, dict) or item.get("pass") is not True:
                issues.append(issue("CROSS_PAGE_CONSISTENCY_FAILED", canonical_issue_message('CROSS_PAGE_CONSISTENCY_FAILED'))); continue
            evidence = _run_path(run_root, str(item.get("evidencePath", "")))
            if not evidence.is_file() or item.get("evidenceSha256") != sha256_file(evidence):
                issues.append(issue("CROSS_PAGE_EVIDENCE_INVALID", canonical_issue_message('CROSS_PAGE_EVIDENCE_INVALID')))
            linked = set(unique_nonempty(item.get("toolExecutionIds", [])))
            if not linked or any(execution_map.get(value, {}).get("exitCode") != 0 for value in linked):
                issues.append(issue("CROSS_PAGE_TOOL_LINK_INVALID", canonical_issue_message('CROSS_PAGE_TOOL_LINK_INVALID')))
    if review.get("decision") != "approved":
        issues.append(issue("REVIEW_DECISION_NOT_APPROVED", canonical_issue_message('REVIEW_DECISION_NOT_APPROVED')))
    blocking = [item for item in review.get("unresolvedIssues", []) if isinstance(item, dict) and item.get("severity") in {"critical", "major"} and item.get("status") != "resolved"]
    if blocking:
        issues.append(issue("BLOCKING_REVIEW_ISSUES_REMAIN", canonical_issue_message('BLOCKING_REVIEW_ISSUES_REMAIN'), count=len(blocking)))
    _require_no_omissions(review, issues, 'review ledger')
    return issues


def gate_test(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    report = _read_required_json(run_root / "test" / "test-report.json", issues, "TEST_REPORT_MISSING") or {}
    if report.get("apkInstallationPolicy") != "forbidden":
        issues.append(issue("APK_INSTALL_POLICY_NOT_FORBIDDEN", canonical_issue_message('APK_INSTALL_POLICY_NOT_FORBIDDEN')))
    discovery = report.get("toolDiscovery", {})
    discovery_path = _run_path(run_root, str(discovery.get("path", "")))
    if not discovery_path.is_file() or discovery.get("sha256") != sha256_file(discovery_path):
        issues.append(issue("TOOL_DISCOVERY_EVIDENCE_MISSING", canonical_issue_message('TOOL_DISCOVERY_EVIDENCE_MISSING')))

    executions = report.get("toolExecutions", []) if isinstance(report, dict) else []
    if not executions:
        issues.append(issue("TOOL_EXECUTIONS_MISSING", canonical_issue_message('TOOL_EXECUTIONS_MISSING')))
    execution_ids: set[str] = set()
    passed_tool_ids: set[str] = set()
    apk_artifacts: list[Path] = []
    for execution in executions:
        if not isinstance(execution, dict):
            issues.append(issue("TOOL_EXECUTION_INVALID", canonical_issue_message('TOOL_EXECUTION_INVALID'))); continue
        execution_id = str(execution.get("executionId", ""))
        tool_id = str(execution.get("toolId", ""))
        if not execution_id or execution_id in execution_ids:
            issues.append(issue("TOOL_EXECUTION_ID_INVALID", canonical_issue_message('TOOL_EXECUTION_ID_INVALID'), executionId=execution_id))
        execution_ids.add(execution_id)
        forbidden = command_forbidden(str(execution.get("command", "")))
        if forbidden:
            issues.append(issue("APK_INSTALL_COMMAND_DETECTED", canonical_issue_message('APK_INSTALL_COMMAND_DETECTED'), executionId=execution_id, pattern=forbidden))
        if execution.get("exitCode") != 0 or execution.get("status") != "passed" or execution.get("timedOut") is True:
            issues.append(issue("TOOL_EXECUTION_FAILED", canonical_issue_message('TOOL_EXECUTION_FAILED'), executionId=execution_id, toolId=tool_id, exitCode=execution.get("exitCode")))
        else:
            passed_tool_ids.add(tool_id)
            passed_tool_ids.update(str(value) for value in execution.get("satisfiesToolIds", []) if value)
        log_path = _run_path(run_root, str(execution.get("logPath", "")))
        if not log_path.is_file() or not is_inside(log_path, run_root) or log_path.stat().st_size < 1:
            issues.append(issue("TOOL_LOG_MISSING", canonical_issue_message('TOOL_LOG_MISSING'), executionId=execution_id))
        elif execution.get("logSha256") != sha256_file(log_path):
            issues.append(issue("TOOL_LOG_HASH_MISMATCH", canonical_issue_message('TOOL_LOG_HASH_MISMATCH'), executionId=execution_id))
        for artifact in execution.get("artifacts", []):
            if not isinstance(artifact, dict) or artifact.get("missing") is True:
                issues.append(issue("TOOL_ARTIFACT_MISSING", canonical_issue_message('TOOL_ARTIFACT_MISSING'), executionId=execution_id, artifact=artifact)); continue
            artifact_path = Path(str(artifact.get("path", "")))
            if artifact.get("directory") is True:
                if not artifact_path.is_dir():
                    issues.append(issue("TOOL_ARTIFACT_DIRECTORY_MISSING", canonical_issue_message('TOOL_ARTIFACT_DIRECTORY_MISSING'), path=artifact_path.as_posix()))
                else:
                    current_directory = directory_artifact_record(artifact_path)
                    if (
                        artifact.get("sha256") != current_directory.get("sha256")
                        or artifact.get("fileCount") != current_directory.get("fileCount")
                        or int(artifact.get("fileCount", 0) or 0) < 1
                    ):
                        issues.append(issue(
                            "TOOL_ARTIFACT_DIRECTORY_HASH_MISMATCH",
                            "A recorded artifact directory is empty or its recursive hash has changed.",
                            path=artifact_path.as_posix(),
                        ))
            elif not artifact_path.is_file() or artifact.get("sha256") != sha256_file(artifact_path):
                issues.append(issue("TOOL_ARTIFACT_HASH_MISMATCH", canonical_issue_message('TOOL_ARTIFACT_HASH_MISMATCH'), path=artifact_path.as_posix()))

    apk_artifacts = [
        Path(str(artifact.get("path", "")))
        for execution in executions if isinstance(execution, dict)
        for artifact in execution.get("artifacts", []) if isinstance(artifact, dict)
        if artifact.get("missing") is not True
        and Path(str(artifact.get("path", ""))).suffix.lower() == ".apk"
        and Path(str(artifact.get("path", ""))).is_file()
        and artifact.get("sha256") == sha256_file(Path(str(artifact.get("path", ""))))
    ]
    expected_tools = set(canonical_required_tool_ids(
        str(state.get("targetPipeline", "web-responsive")),
        Path(str(state.get("projectRoot", "."))).resolve(),
    ))
    missing_tools = sorted(expected_tools - passed_tool_ids)
    if missing_tools:
        issues.append(issue("TARGET_TOOLCHAIN_COVERAGE_INCOMPLETE", canonical_issue_message('TARGET_TOOLCHAIN_COVERAGE_INCOMPLETE'), expected=sorted(expected_tools), passed=sorted(passed_tool_ids), missing=missing_tools))

    target = str(state.get("targetPipeline", ""))
    if target in {"web-responsive", "app-mobile-webview", "cross-platform"}:
        web_build_directories = [
            Path(str(artifact.get("path", "")))
            for execution in executions if isinstance(execution, dict) and execution.get("toolId") == "web-build"
            for artifact in execution.get("artifacts", []) if isinstance(artifact, dict)
            if artifact.get("directory") is True and artifact.get("missing") is not True
            and Path(str(artifact.get("path", ""))).is_dir()
        ]
        if not web_build_directories:
            issues.append(issue("WEB_BUILD_ARTIFACT_MISSING", "Web verification requires a physical deployable build directory."))
        for build_root in web_build_directories:
            build_files = [path for path in build_root.rglob("*") if path.is_file()]
            lower_names = [path.relative_to(build_root).as_posix().lower() for path in build_files]
            has_entry = any(name.endswith((".html", "routes-manifest.json", "app-paths-manifest.json")) for name in lower_names)
            required_groups = {
                "entry-or-route-manifest": has_entry,
                "javascript": any(name.endswith((".js", ".mjs")) for name in lower_names),
                "css": any(name.endswith(".css") for name in lower_names),
            }
            design_pages = (read_json(run_root / "design" / "design-ledger.json", {}) or {}).get("pages", [])
            if any(isinstance(page, dict) and page.get("imageStrategy", {}).get("required") is True for page in design_pages):
                required_groups["image"] = any(name.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg")) for name in lower_names)
            for group, present in required_groups.items():
                if not present:
                    issues.append(issue(
                        "WEB_BUILD_CONTENT_MISSING",
                        "The deployable web build is missing a required content group.",
                        path=build_root.as_posix(),
                        contentGroup=group,
                    ))
    if target in {"app-mobile-webview", "cross-platform"}:
        if not apk_artifacts:
            issues.append(issue("WEBVIEW_APK_ARTIFACT_MISSING", "WebView app verification requires a physically built APK artifact."))
        for apk_path in apk_artifacts:
            try:
                with zipfile.ZipFile(apk_path) as archive:
                    names = [name.lower() for name in archive.namelist()]
            except (OSError, zipfile.BadZipFile):
                issues.append(issue("WEBVIEW_APK_INVALID", "The recorded APK artifact cannot be opened as an Android package.", path=apk_path.as_posix()))
                continue
            required_groups = {
                "html": (".html",),
                "css": (".css",),
                "javascript": (".js", ".mjs"),
                "image": (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"),
            }
            for group, suffixes in required_groups.items():
                if not any(name.startswith("assets/") and name.endswith(suffixes) for name in names):
                    issues.append(issue(
                        "WEBVIEW_APK_ASSET_MISSING",
                        "The built APK is missing a required WebView asset group.",
                        path=apk_path.as_posix(),
                        assetGroup=group,
                    ))
    pages = (read_json(run_root / "design" / "page-inventory.json", {}) or {}).get("pages", [])
    expected_pages = {str(item.get("pageId", "")) for item in pages if isinstance(item, dict)}
    checked: set[str] = set()
    for item in report.get("pageVisualChecks", []):
        _physical_evidence_item(run_root, item, execution_ids, "pageVisualChecks", issues)
        if isinstance(item, dict) and item.get("pass") is True:
            checked.add(str(item.get("pageId", "")))
    if checked != expected_pages:
        issues.append(issue("VISUAL_TEST_COVERAGE_INCOMPLETE", canonical_issue_message('VISUAL_TEST_COVERAGE_INCOMPLETE'), expected=sorted(expected_pages), checked=sorted(checked)))

    for group in ["accessibilityChecks", "responsiveChecks", "securityChecks", "stateChecks", "performanceChecks", "visualRegressionChecks"]:
        values = report.get(group, [])
        if not values:
            issues.append(issue(f"{group.upper()}_INCOMPLETE", "KH_Aw blocked this stage because required evidence is incomplete."))
            continue
        for item in values:
            _physical_evidence_item(run_root, item, execution_ids, group, issues)

    if target in {"android-native", "app-mobile-webview", "cross-platform", "ios-native"}:
        checks = report.get("emulatorSimulatorChecks", [])
        if not checks:
            issues.append(issue("EMULATOR_SIMULATOR_EVIDENCE_MISSING", canonical_issue_message('EMULATOR_SIMULATOR_EVIDENCE_MISSING')))
        for item in checks:
            _physical_evidence_item(run_root, item, execution_ids, "emulatorSimulatorChecks", issues)

    blocking = [item for item in report.get("unresolvedIssues", []) if isinstance(item, dict) and item.get("severity") in {"critical", "major"} and item.get("status") != "resolved"]
    if blocking:
        issues.append(issue("BLOCKING_TEST_ISSUES_REMAIN", canonical_issue_message('BLOCKING_TEST_ISSUES_REMAIN'), count=len(blocking)))
    if report.get("releaseDecision") != "approved":
        issues.append(issue("RELEASE_DECISION_NOT_APPROVED", canonical_issue_message('RELEASE_DECISION_NOT_APPROVED')))
    if state.get("analysisMode") == "analysis-folder-provided":
        snapshot = compare_snapshot(run_root)
        if not snapshot.get("ok"):
            issues.append(issue("ANALYSIS_FOLDER_MUTATED", canonical_issue_message('ANALYSIS_FOLDER_MUTATED'), **snapshot))
    _require_no_omissions(report, issues, 'test report')
    return issues


def _open_repair_tickets(run_root: Path) -> list[str]:
    open_tickets: list[str] = []
    repairs = run_root / "repairs"
    if not repairs.is_dir():
        return open_tickets
    for path in repairs.rglob("repair-ticket.json"):
        payload = read_json(path, {})
        if payload.get("status") != "closed":
            open_tickets.append(path.relative_to(run_root).as_posix())
    return sorted(open_tickets)


def _gate_session_forensics(run_root: Path) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    ledger = _read_required_json(
        run_root / "audit" / "session-forensics.json",
        issues,
        "SESSION_FORENSICS_MISSING",
    ) or {}
    if len(str(ledger.get("sessionId", "")).strip()) < 8:
        issues.append(issue("SESSION_FORENSICS_SESSION_MISSING", "Session forensics must identify the Codex session."))
    source_session = Path(str(ledger.get("sourceSessionPath", ""))).expanduser()
    if (
        not source_session.is_file()
        or ledger.get("sourceSessionSha256") != (sha256_file(source_session) if source_session.is_file() else "")
        or int(ledger.get("sourceSessionEventCount", 0) or 0) < 1
        or int(ledger.get("sourceSessionParseErrors", 0) or 0) != 0
    ):
        issues.append(issue("SESSION_FORENSICS_SOURCE_INVALID", "Session forensics must be generated from a valid physical Codex JSONL session with a matching hash."))
    if not isinstance(ledger.get("commands"), list) or not ledger.get("commands"):
        issues.append(issue("SESSION_FORENSICS_COMMANDS_MISSING", "Session forensics must list the commands and native actions that were actually executed."))
    if ledger.get("notRunRequiredChecks"):
        issues.append(issue("SESSION_FORENSICS_REQUIRED_CHECK_NOT_RUN", "A required check is recorded as not run.", checks=ledger.get("notRunRequiredChecks")))
    if ledger.get("evidenceMismatches"):
        issues.append(issue("SESSION_FORENSICS_EVIDENCE_MISMATCH", "Session evidence and final claims do not match.", mismatches=ledger.get("evidenceMismatches")))
    if ledger.get("completionTruth") != "verified":
        issues.append(issue("SESSION_FORENSICS_NOT_VERIFIED", "Session forensics must set completionTruth to verified only after evidence comparison."))
    findings = ledger.get("slashCapabilityFindings", [])
    if not isinstance(findings, list) or not findings:
        issues.append(issue("SESSION_FORENSICS_SLASH_AUDIT_MISSING", "Session forensics must audit actual slash capability use."))
    _require_no_omissions(ledger, issues, "session forensics")
    return issues


def gate_release(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    issues.extend(_gate_session_forensics(run_root))
    for stage in STAGES[:-1]:
        if not stage_status_passed(state.get("stageStatus", {}).get(stage, "")):
            issues.append(issue("PREVIOUS_STAGE_NOT_PASSED", canonical_issue_message('PREVIOUS_STAGE_NOT_PASSED'), stage=stage, status=state.get("stageStatus", {}).get(stage)))
    release = _read_required_json(run_root / "release" / "release.json", issues, "RELEASE_MANIFEST_MISSING") or {}
    for field in ["version", "artifacts", "installation", "rollback", "privacy", "support", "costLedger", "releaseNotes"]:
        if not nonempty(release.get(field)):
            issues.append(issue("RELEASE_FIELD_MISSING", canonical_issue_message('RELEASE_FIELD_MISSING'), field=field))
    for artifact in release.get("artifacts", []):
        if not isinstance(artifact, dict):
            issues.append(issue("RELEASE_ARTIFACT_INVALID", canonical_issue_message('RELEASE_ARTIFACT_INVALID'))); continue
        path = safe_resolve(artifact.get("path", ""), Path(str(state.get("projectRoot", ""))))
        if not path.is_file() or artifact.get("sha256") != sha256_file(path):
            issues.append(issue("RELEASE_ARTIFACT_HASH_MISMATCH", canonical_issue_message('RELEASE_ARTIFACT_HASH_MISMATCH'), path=path.as_posix()))
    scan = release.get("securityScan", {})
    user_report = _run_path(run_root, str(release.get("userReportPath", "")))
    if not user_report.is_file() or not is_inside(user_report, run_root):
        issues.append(issue("KOREAN_USER_REPORT_MISSING", "Release requires a Korean report that the user can read in the IDE panel."))
    else:
        if release.get("userReportSha256") != sha256_file(user_report):
            issues.append(issue("KOREAN_USER_REPORT_HASH_MISMATCH", "The Korean user report hash does not match the physical file."))
        if korean_ui_character_count([user_report]) < 20:
            issues.append(issue("KOREAN_USER_REPORT_CONTENT_INSUFFICIENT", "The user-facing release report must contain meaningful Korean explanation."))
    if scan.get("status") != "passed" or scan.get("findings"):
        issues.append(issue("RELEASE_SECURITY_SCAN_FAILED", canonical_issue_message('RELEASE_SECURITY_SCAN_FAILED'), scan=scan))
    open_tickets = _open_repair_tickets(run_root)
    if open_tickets:
        issues.append(issue("OPEN_REPAIR_TICKETS_REMAIN", canonical_issue_message('OPEN_REPAIR_TICKETS_REMAIN'), tickets=open_tickets))
    if release.get("openRepairTickets"):
        issues.append(issue("RELEASE_LEDGER_OPEN_TICKETS_REMAIN", canonical_issue_message('RELEASE_LEDGER_OPEN_TICKETS_REMAIN')))
    if state.get("analysisMode") == "analysis-folder-provided":
        snapshot = compare_snapshot(run_root)
        if not snapshot.get("ok"):
            issues.append(issue("ANALYSIS_FOLDER_MUTATED", canonical_issue_message('ANALYSIS_FOLDER_MUTATED'), **snapshot))
    _require_no_omissions(release, issues, 'release ledger')
    return issues


GATE_FUNCTIONS: dict[str, Callable[[Path, dict[str, Any]], list[dict[str, Any]]]] = {
    "intake": gate_intake,
    "analyze": gate_analyze,
    "research": gate_research,
    "design": gate_design,
    "implement": gate_implement,
    "review": gate_review,
    "test": gate_test,
    "release": gate_release,
}


def run_gate(run_root: Path, state: dict[str, Any], stage: str, *, enforce_order: bool = True) -> dict[str, Any]:
    if stage not in GATE_FUNCTIONS:
        raise ValueError(f"Unknown stage: {stage}")
    issues: list[dict[str, Any]] = []
    issues.extend(verify_run_lock(run_root, state))
    issues.extend(_gate_target_pipeline(run_root, state))
    if enforce_order:
        previous_ok, missing = _all_previous_passed(state, stage)
        if not previous_ok:
            issues.append(issue("STAGE_ORDER_VIOLATION", canonical_issue_message('STAGE_ORDER_VIOLATION'), requestedStage=stage, missingStages=missing))
    issues.extend(GATE_FUNCTIONS[stage](run_root, state))
    issues.extend(_gate_requirement_coverage(run_root, state, stage))
    issues.extend(internal_language_issues(run_root))
    issues.extend(orchestration_issues(run_root, state, stage))
    issues.extend(_gate_native_capabilities(run_root, stage))
    result = {
        "schemaVersion": "3.0",
        "checkedAt": utc_now(),
        "stage": stage,
        "pass": len(issues) == 0,
        "issueCount": len(issues),
        "issues": issues,
    }
    report_path = run_root / "reports" / f"gate-{stage}.json"
    write_json(report_path, result)
    event_path = run_root / "reports" / "gate-events.jsonl"
    event_path.parent.mkdir(parents=True, exist_ok=True)
    with event_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({
            "event": "gate-completed",
            "stage": stage,
            "pass": result["pass"],
            "issueCount": result["issueCount"],
            "reportPath": report_path.relative_to(run_root).as_posix(),
            "reportSha256": sha256_file(report_path),
            "at": result["checkedAt"],
        }, ensure_ascii=False) + "\n")
    return result
