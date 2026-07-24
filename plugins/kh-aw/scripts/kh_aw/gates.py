from __future__ import annotations

import json
import re
import struct
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from .capabilities import NATIVE_CAPABILITIES, capability_records_for_stage
from .contracts import RESEARCH_CATEGORIES, STAGES, scan_forbidden_manual_keys
from .tooling import canonical_required_tool_ids, command_forbidden, required_tool_ids
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
    "robot check", "cloudflare ray id", "로그인이 필요", "접근이 거부",
}
PUBLIC_VISIBILITIES = {"public", "authenticated", "customer", "user"}
STATIC_EXCEPTION_VISIBILITIES = {"legal", "system", "internal", "admin-static"}


def issue(code: str, message: str, severity: str = "major", **evidence: Any) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, "evidence": evidence}


def _read_required_json(path: Path, issues: list[dict[str, Any]], code: str) -> Any:
    value = read_json(path, None)
    if value is None:
        issues.append(issue(code, f"필수 JSON 파일이 없거나 올바르지 않습니다: {path}"))
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
        issues.append(issue("DECLARED_OMISSIONS_REMAIN", f"{label}에 누락 항목이 남아 있습니다.", omissions=payload.get("omissions")))


def _require_unique_ids(items: Any, key: str, code: str, label: str, issues: list[dict[str, Any]]) -> set[str]:
    values = _ids(items, key)
    empty_count = sum(1 for value in values if not value)
    duplicates = _duplicates([value for value in values if value])
    if empty_count or duplicates or not values:
        issues.append(issue(code, f"{label} ID는 비어 있지 않고 중복되지 않아야 합니다.", emptyCount=empty_count, duplicates=duplicates, count=len(values)))
    return {value for value in values if value}


def _all_previous_passed(state: dict[str, Any], stage: str) -> tuple[bool, list[str]]:
    index = STAGES.index(stage)
    missing = [name for name in STAGES[:index] if not str(state.get("stageStatus", {}).get(name, "")).startswith("passed")]
    return not missing, missing




def _gate_native_capabilities(run_root: Path, stage: str) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    required, records = capability_records_for_stage(run_root, stage)
    record_map = {str(item.get("capabilityId")): item for item in records if isinstance(item, dict)}
    for definition in required:
        capability_id = str(definition.get("id", ""))
        record = record_map.get(capability_id)
        if not record:
            issues.append(issue("NATIVE_CAPABILITY_EVIDENCE_MISSING", "Codex 네이티브/슬러시 기능 또는 물리 fallback 실행 증거가 없습니다.", stage=stage, capabilityId=capability_id, preferredSlash=definition.get("preferredSlash")))
            continue
        path = _run_path(run_root, str(record.get("evidencePath", "")))
        if not path.is_file() or not is_inside(path, run_root) or path.stat().st_size < 16:
            issues.append(issue("NATIVE_CAPABILITY_EVIDENCE_INVALID", "네이티브 기능 증거 파일이 없거나 너무 작습니다.", capabilityId=capability_id, path=record.get("evidencePath")))
            continue
        if record.get("evidenceSha256") != sha256_file(path):
            issues.append(issue("NATIVE_CAPABILITY_HASH_MISMATCH", "네이티브 기능 증거 해시가 일치하지 않습니다.", capabilityId=capability_id))
        if record.get("mode") not in {"native", "fallback"} or record.get("status") != "verified" or not str(record.get("invocation", "")).strip():
            issues.append(issue("NATIVE_CAPABILITY_RECORD_INVALID", "네이티브 기능 기록의 mode/status/invocation이 유효하지 않습니다.", capabilityId=capability_id))
    return issues


def _physical_evidence_item(run_root: Path, item: Any, execution_ids: set[str], label: str, issues: list[dict[str, Any]]) -> None:
    if not isinstance(item, dict) or item.get("pass") is not True:
        issues.append(issue("PHYSICAL_TEST_EVIDENCE_INVALID", f"{label} 항목은 pass=true 객체여야 합니다.", item=item))
        return
    path_raw = str(item.get("evidencePath", ""))
    path = _run_path(run_root, path_raw)
    if not path.is_file() or not is_inside(path, run_root) or path.stat().st_size < 1:
        issues.append(issue("PHYSICAL_TEST_EVIDENCE_MISSING", f"{label}의 실제 증거 파일이 없습니다.", path=path_raw))
        return
    if item.get("evidenceSha256") != sha256_file(path):
        issues.append(issue("PHYSICAL_TEST_EVIDENCE_HASH_MISMATCH", f"{label} 증거 SHA-256이 일치하지 않습니다.", path=path_raw))
    linked = set(unique_nonempty(item.get("toolExecutionIds", [])))
    if not linked or not linked.issubset(execution_ids):
        issues.append(issue("PHYSICAL_TEST_TOOL_LINK_INVALID", f"{label} 증거가 실제 도구 실행 ID와 연결되지 않았습니다.", linked=sorted(linked)))


def gate_intake(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    issues.extend(verify_run_lock(run_root, state))
    requirements = _read_required_json(run_root / "contract" / "requirements.json", issues, "REQUIREMENTS_MISSING") or {}
    instruction_path = Path(str(state.get("instructionsFile", "")))
    instructions = instruction_path.read_text(encoding="utf-8", errors="replace") if instruction_path.is_file() else ""
    expected = exact_instruction_lines(instructions)
    coverage = requirements.get("rawInstructionCoverage", []) if isinstance(requirements, dict) else []
    actual = [str(item.get("sourceText", "")).rstrip() for item in coverage if isinstance(item, dict)]
    if not expected:
        issues.append(issue("USER_INSTRUCTIONS_EMPTY", "사용자 원문 지시 파일이 비어 있습니다."))
    if expected != actual:
        issues.append(issue(
            "RAW_INSTRUCTION_ONE_TO_ONE_REQUIRED",
            "사용자 지시 원문이 순서·문장 그대로 1:1 보존되지 않았습니다.",
            expectedCount=len(expected), actualCount=len(actual),
        ))
    requirements_list = requirements.get("requirements", []) if isinstance(requirements, dict) else []
    raw_ids = _require_unique_ids(coverage, "id", "RAW_IDS_INVALID", "원문", issues)
    req_ids = _require_unique_ids(requirements_list, "id", "REQUIREMENT_IDS_INVALID", "요구사항", issues)
    if len(requirements_list) != len(expected):
        issues.append(issue("REQUIREMENT_COUNT_MISMATCH", "각 원문 지시마다 독립 요구사항 ID가 필요합니다.", expected=len(expected), actual=len(requirements_list)))
    for item in coverage:
        if not isinstance(item, dict):
            continue
        linked = set(unique_nonempty(item.get("requirementIds", [])))
        if not linked or not linked.issubset(req_ids):
            issues.append(issue("RAW_REQUIREMENT_LINK_INVALID", "원문 줄이 존재하는 요구사항 ID와 연결되지 않았습니다.", rawId=item.get("id"), linked=sorted(linked)))
    source_ids = {str(item.get("source", "")) for item in requirements_list if isinstance(item, dict)}
    if source_ids != raw_ids:
        issues.append(issue("REQUIREMENT_SOURCE_COVERAGE_INCOMPLETE", "모든 원문 ID가 요구사항 source로 정확히 연결되어야 합니다.", expected=sorted(raw_ids), actual=sorted(source_ids)))
    forbidden = scan_forbidden_manual_keys(requirements)
    if forbidden:
        issues.append(issue("MANUAL_DESIGN_SELECTION_FORBIDDEN", "수동 컨셉/색상 선택 키가 요구사항 계약에 포함되어 있습니다.", paths=forbidden))
    tool_policy = _read_required_json(run_root / "contract" / "tool-policy.json", issues, "TOOL_POLICY_MISSING") or {}
    if tool_policy.get("apkInstallation", {}).get("status") != "forbidden":
        issues.append(issue("APK_INSTALL_EXCLUSION_NOT_LOCKED", "사용자 지시대로 APK 설치 제외 정책이 계약에 고정되어야 합니다."))
    policy_ids = [str(item.get("id", "")) for item in tool_policy.get("requiredTools", []) if isinstance(item, dict) and item.get("required") is True]
    canonical_tool_ids = canonical_required_tool_ids(
        str(state.get("targetPipeline", "web-responsive")),
        Path(str(state.get("projectRoot", "."))).resolve(),
    )
    if policy_ids != canonical_tool_ids:
        issues.append(issue("TARGET_TOOL_POLICY_TAMPERED", "대상 플랫폼의 필수 도구 목록은 엔진 정식 계약과 정확히 일치해야 합니다.", expected=canonical_tool_ids, actual=policy_ids))
    capability_policy = _read_required_json(run_root / "contract" / "native-capability-policy.json", issues, "NATIVE_CAPABILITY_POLICY_MISSING") or {}
    policy_capability_ids = [str(item.get("id", "")) for item in capability_policy.get("capabilities", []) if isinstance(item, dict) and item.get("required") is True]
    canonical_capability_ids = [str(item.get("id", "")) for item in NATIVE_CAPABILITIES if item.get("required") is True]
    if policy_capability_ids != canonical_capability_ids:
        issues.append(issue("NATIVE_CAPABILITY_POLICY_TAMPERED", "네이티브/슬러시 기능 필수 목록은 엔진 정식 계약과 정확히 일치해야 합니다.", expected=canonical_capability_ids, actual=policy_capability_ids))
    _require_no_omissions(requirements, issues, "요구사항 계약")
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
        issues.append(issue("PROJECT_KIND_UNRESOLVED", "projectKind는 existing 또는 greenfield여야 합니다."))
    if file_count <= 0 and not (project_kind == "greenfield" and len(str(ledger.get("greenfieldJustification", ""))) >= 30):
        issues.append(issue("ANALYSIS_INVENTORY_EMPTY", "빈 신규 프로젝트라면 greenfield 근거를 기록하고, 기존 프로젝트라면 전체 파일 원장이 필요합니다."))
    inventory_jsonl = Path(str(inventory.get("inventoryJsonl", "")))
    if not inventory_jsonl.is_file():
        issues.append(issue("ANALYSIS_INVENTORY_JSONL_MISSING", "파일별 SHA-256 전수 원장이 없습니다."))
    else:
        with inventory_jsonl.open("r", encoding="utf-8", errors="replace") as stream:
            inventory_rows = sum(1 for _ in stream)
        if file_count != inventory_rows:
            issues.append(issue("ANALYSIS_INVENTORY_COUNT_MISMATCH", "전수 원장 행 수와 요약 파일 수가 일치하지 않습니다."))
    required_fields = [
        "projectSummary", "techStack", "architecture", "requirementCoverage", "pageInventory",
        "logicInventory", "featureInventory", "fileFindings", "logicFindings", "strengths",
        "weaknesses", "risks", "upgradeTargets",
    ]
    for field in required_fields:
        if not nonempty(ledger.get(field)):
            issues.append(issue("ANALYSIS_FIELD_INCOMPLETE", f"심층 분석 장부 필수 항목이 비어 있습니다: {field}", field=field))
    if ledger.get("projectStructure", {}).get("fileCount") != file_count:
        issues.append(issue("ANALYSIS_FILE_COUNT_TRACE_MISMATCH", "분석 장부 파일 수가 전수 원장과 일치하지 않습니다.", inventory=file_count, ledger=ledger.get("projectStructure", {}).get("fileCount")))
    coverage_ids = {str(item.get("requirementId", item.get("id", ""))) for item in ledger.get("requirementCoverage", []) if isinstance(item, dict)}
    if coverage_ids != req_ids:
        issues.append(issue("ANALYSIS_REQUIREMENT_COVERAGE_INCOMPLETE", "분석 장부가 모든 요구사항 ID를 1:1 다루지 않습니다.", expected=sorted(req_ids), actual=sorted(coverage_ids)))
    page_ids = _require_unique_ids(ledger.get("pageInventory", []), "pageId", "ANALYSIS_PAGE_IDS_INVALID", "분석 페이지", issues)
    field_ids = _require_unique_ids(ledger.get("fieldInventory", []), "fieldId", "ANALYSIS_FIELD_IDS_INVALID", "분석 필드", issues) if ledger.get("fieldInventory") else set()
    logic_ids = _require_unique_ids(ledger.get("logicInventory", []), "logicId", "ANALYSIS_LOGIC_IDS_INVALID", "분석 로직", issues)
    feature_ids = _require_unique_ids(ledger.get("featureInventory", []), "featureId", "ANALYSIS_FEATURE_IDS_INVALID", "분석 기능", issues)
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
                issues.append(issue(code, "페이지가 존재하지 않는 분석 ID를 참조합니다.", pageId=pid, field=key, unknown=unknown))
        if not nonempty(page.get("requiredRegions")) or not nonempty(page.get("states")):
            issues.append(issue("PAGE_ANALYSIS_STRUCTURE_INCOMPLETE", "각 페이지에는 requiredRegions와 states가 필요합니다.", pageId=pid))
    minimum_findings = 1 if file_count == 0 else min(20, max(5, file_count // 100 + 5))
    if len(ledger.get("fileFindings", [])) < minimum_findings:
        issues.append(issue("ANALYSIS_FILE_FINDINGS_TOO_SHALLOW", "핵심 파일별 조사 근거가 범위에 비해 적습니다.", requiredMinimum=minimum_findings, actual=len(ledger.get("fileFindings", []))))
    mode = state.get("analysisMode")
    if mode not in {"analysis-folder-provided", "analysis-folder-not-provided"}:
        issues.append(issue("ANALYSIS_MODE_UNRESOLVED", "분석폴더 제공 여부가 코드 상태로 확정되지 않았습니다."))
    if ledger.get("analysisFolderMode") != mode:
        issues.append(issue("ANALYSIS_MODE_LEDGER_MISMATCH", "분석 장부와 상태 파일의 분석폴더 모드가 다릅니다."))
    if mode == "analysis-folder-provided":
        analysis_folder = Path(str(state.get("analysisFolder", "")))
        workspace_root = Path(str(state.get("workspaceRoot", "")))
        if not analysis_folder.is_dir():
            issues.append(issue("ANALYSIS_FOLDER_MISSING", "지정된 분석폴더가 존재하지 않습니다.", path=analysis_folder.as_posix()))
        if analysis_folder and workspace_root and is_inside(workspace_root, analysis_folder):
            issues.append(issue("OUTPUT_INSIDE_ANALYSIS_FOLDER", "결과물 작업공간이 읽기 전용 분석폴더 내부에 있습니다."))
        snapshot = compare_snapshot(run_root)
        if not snapshot.get("ok"):
            issues.append(issue("ANALYSIS_FOLDER_MUTATED", "분석폴더 원본이 변경되었습니다. 백업에서 자동 복구해야 합니다.", **snapshot))
        evidence = ledger.get("analysisFolderEvidence", {})
        if evidence.get("snapshotFileCount") != snapshot.get("expectedCount") or not evidence.get("readOnlyPolicyConfirmed"):
            issues.append(issue("ANALYSIS_FOLDER_EVIDENCE_INCOMPLETE", "분석 장부에 스냅샷 파일 수와 읽기 전용 정책 확인이 필요합니다."))
    forbidden = scan_forbidden_manual_keys(ledger)
    if forbidden:
        issues.append(issue("MANUAL_DESIGN_SELECTION_FORBIDDEN", "분석 장부에 수동 컨셉/색상 선택 키가 남아 있습니다.", paths=forbidden))
    _require_no_omissions(ledger, issues, "분석 장부")
    return issues


def _validate_source(run_root: Path, source: dict[str, Any], issues: list[dict[str, Any]]) -> bool:
    sid = str(source.get("id", ""))
    url = str(source.get("url", ""))
    stype = str(source.get("sourceType", "")).lower()
    valid = True
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        issues.append(issue("SOURCE_URL_INVALID", "출처 URL이 유효한 절대 HTTP(S) URL이 아닙니다.", sourceId=sid, url=url)); valid = False
    if parsed.netloc.lower() in SEARCH_HOSTS:
        issues.append(issue("SEARCH_RESULT_IS_NOT_BODY_EVIDENCE", "검색결과 페이지 자체는 본문 증거가 아닙니다.", sourceId=sid, url=url)); valid = False
    body_path = _run_path(run_root, str(source.get("bodyPath", "")))
    text_path = _run_path(run_root, str(source.get("textPath", "")))
    if not is_inside(body_path, run_root) or not body_path.is_file() or body_path.stat().st_size < 500:
        issues.append(issue("SOURCE_BODY_MISSING_OR_TOO_SMALL", "실제 원문 본문 파일이 없거나 너무 작습니다.", sourceId=sid)); return False
    if source.get("bodySha256") != sha256_file(body_path):
        issues.append(issue("SOURCE_BODY_HASH_MISMATCH", "본문 증거 해시가 현재 파일과 일치하지 않습니다.", sourceId=sid)); valid = False
    extracted = text_path.read_text(encoding="utf-8", errors="replace") if text_path.is_file() and is_inside(text_path, run_root) else ""
    if len(extracted.strip()) < 500 or int(source.get("extractedCharacters", 0) or 0) < 500:
        issues.append(issue("SOURCE_BODY_EXTRACTION_INSUFFICIENT", "URL·제목·스니펫 수준이 아니라 본문 500자 이상을 직접 추출해야 합니다.", sourceId=sid, characters=len(extracted.strip()))); valid = False
    lower = extracted[:5000].lower()
    if any(marker in lower for marker in BLOCK_PAGE_MARKERS):
        issues.append(issue("SOURCE_BLOCK_OR_LOGIN_PAGE_REJECTED", "차단·로그인·CAPTCHA 페이지는 본문 증거가 아닙니다.", sourceId=sid)); valid = False
    status = int(source.get("httpStatus", 0) or 0)
    if not 200 <= status < 400:
        issues.append(issue("SOURCE_HTTP_STATUS_REJECTED", "성공 HTTP 본문이 아닙니다.", sourceId=sid, status=status)); valid = False
    if len(str(source.get("projectFitReason", "")).strip()) < 50:
        issues.append(issue("SOURCE_PROJECT_FIT_UNPROVEN", "현재 프로젝트에 맞는 구체적 적용 이유가 50자 이상 필요합니다.", sourceId=sid)); valid = False
    if stype not in {"web", "github", "official"}:
        issues.append(issue("SOURCE_TYPE_INVALID", "출처 유형은 web/github/official 중 하나여야 합니다.", sourceId=sid, sourceType=stype)); valid = False
    return valid


def gate_research(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    requirements = _read_required_json(run_root / "contract" / "requirements.json", issues, "REQUIREMENTS_MISSING") or {}
    plan = _read_required_json(run_root / "evidence" / "research-plan.json", issues, "RESEARCH_PLAN_MISSING") or {}
    registry = _read_required_json(run_root / "evidence" / "source-registry.json", issues, "SOURCE_REGISTRY_MISSING") or {}
    forbidden = scan_forbidden_manual_keys(plan)
    if forbidden:
        issues.append(issue("MANUAL_DESIGN_SELECTION_FORBIDDEN", "연구 계획에 수동 컨셉/색상 선택이 남아 있습니다.", paths=forbidden))
    elements = plan.get("elements", []) if isinstance(plan, dict) else []
    element_ids = _require_unique_ids(elements, "id", "RESEARCH_ELEMENT_IDS_INVALID", "연구 요소", issues)
    categories = {str(item.get("category", "")) for item in elements if isinstance(item, dict)}
    missing_categories = [category for category in RESEARCH_CATEGORIES if category not in categories]
    if missing_categories:
        issues.append(issue("RESEARCH_CATEGORY_COVERAGE_INCOMPLETE", "필수 연구 영역이 누락되었습니다.", missing=missing_categories))
    requirement_ids = {item.get("id") for item in requirements.get("requirements", []) if isinstance(item, dict)}
    linked_ids = {rid for element in elements if isinstance(element, dict) for rid in element.get("requirementIds", [])}
    missing_links = sorted(rid for rid in requirement_ids if rid and rid not in linked_ids)
    if missing_links:
        issues.append(issue("RESEARCH_REQUIREMENT_LINKS_INCOMPLETE", "모든 요구사항이 연구 요소와 연결되어야 합니다.", missing=missing_links))
    for element in elements:
        if not isinstance(element, dict):
            continue
        eid = str(element.get("id", ""))
        if element.get("status") == "AI_MUST_REPLACE_DYNAMICALLY" or "동적으로 작성" in str(element.get("label", "")):
            issues.append(issue("RESEARCH_PLAN_PLACEHOLDER_REMAINS", "현재 프로젝트에 맞는 실제 연구 계획으로 교체하지 않았습니다.", elementId=eid))
        if len(unique_nonempty(element.get("webQueries", []))) < 2:
            issues.append(issue("WEB_QUERY_MINIMUM_NOT_MET", "각 연구 요소마다 프로젝트 적합 웹 쿼리 2개 이상이 필요합니다.", elementId=eid))
        if len(unique_nonempty(element.get("githubQueries", []))) < 2:
            issues.append(issue("GITHUB_QUERY_MINIMUM_NOT_MET", "각 연구 요소마다 프로젝트 적합 GitHub 쿼리 2개 이상이 필요합니다.", elementId=eid))
        if len(str(element.get("reason", ""))) < 30:
            issues.append(issue("RESEARCH_ELEMENT_REASON_INSUFFICIENT", "연구 요소가 현재 프로젝트에 필요한 이유가 구체적이지 않습니다.", elementId=eid))
    sources = registry.get("sources", []) if isinstance(registry, dict) else []
    _require_unique_ids(sources, "id", "SOURCE_IDS_INVALID", "출처", issues)
    seen_pairs: set[tuple[str, str]] = set()
    valid_by_element: dict[str, dict[str, list[str]]] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        eid = str(source.get("elementId", ""))
        url = str(source.get("url", ""))
        if eid not in element_ids:
            issues.append(issue("SOURCE_ELEMENT_LINK_INVALID", "출처가 존재하지 않는 연구 요소를 참조합니다.", sourceId=source.get("id"), elementId=eid))
        pair = (eid, url)
        if pair in seen_pairs:
            issues.append(issue("DUPLICATE_RESEARCH_SOURCE", "같은 연구 요소에 동일 URL이 중복 등록되었습니다.", elementId=eid, url=url))
        seen_pairs.add(pair)
        if _validate_source(run_root, source, issues):
            bucket = "github" if str(source.get("sourceType", "")).lower() == "github" else "web"
            valid_by_element.setdefault(eid, {"web": [], "github": []})[bucket].append(url)
    for element in elements:
        if not isinstance(element, dict):
            continue
        eid = str(element.get("id", ""))
        required = 1 if element.get("exceptionCode") == "KOREA_ADDRESS_DAUM_POSTCODE" else 2
        buckets = valid_by_element.get(eid, {"web": [], "github": []})
        web_count = len(set(buckets["web"]))
        gh_count = len(set(buckets["github"]))
        if web_count < required or gh_count < required:
            issues.append(issue("BODY_BACKED_SOURCE_MINIMUM_NOT_MET", "각 연구 요소에 유효한 실제 본문 기반 웹/GitHub 출처가 각각 필요 수량만큼 있어야 합니다.", elementId=eid, required=required, web=web_count, github=gh_count))
    _require_no_omissions(plan, issues, "연구 계획")
    return issues


def gate_design(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    analysis = _read_required_json(run_root / "analysis" / "analysis-ledger.json", issues, "ANALYSIS_LEDGER_MISSING") or {}
    inventory = _read_required_json(run_root / "design" / "page-inventory.json", issues, "PAGE_INVENTORY_MISSING") or {}
    ledger = _read_required_json(run_root / "design" / "design-ledger.json", issues, "DESIGN_LEDGER_MISSING") or {}
    registry = _read_required_json(run_root / "evidence" / "source-registry.json", issues, "SOURCE_REGISTRY_MISSING") or {}
    forbidden = scan_forbidden_manual_keys(ledger)
    if forbidden:
        issues.append(issue("MANUAL_DESIGN_SELECTION_FORBIDDEN", "설계 장부에 수동 컨셉/색상 선택이 남아 있습니다.", paths=forbidden))
    origin = ledger.get("designOriginPolicy", {}) if isinstance(ledger, dict) else {}
    if origin.get("mode") not in {"dynamic-web-body-research", "dynamic-web-body-research-plus-existing-brand"}:
        issues.append(issue("DYNAMIC_DESIGN_ORIGIN_REQUIRED", "디자인은 매 프로젝트의 웹 본문 연구에서 동적으로 도출해야 합니다."))
    if origin.get("manualConceptSelection") is not False or origin.get("manualColorSelection") is not False or origin.get("fixedDesignPreset") is not False or origin.get("projectSpecificEveryRun") is not True:
        issues.append(issue("MANUAL_OR_FIXED_DESIGN_POLICY_REJECTED", "수동 선택·고정 프리셋은 false이고 projectSpecificEveryRun은 true여야 합니다."))
    analysis_pages = analysis.get("pageInventory", []) if isinstance(analysis, dict) else []
    pages = inventory.get("pages", []) if isinstance(inventory, dict) else []
    designs = ledger.get("pages", []) if isinstance(ledger, dict) else []
    analysis_ids = _require_unique_ids(analysis_pages, "pageId", "ANALYSIS_PAGE_IDS_INVALID", "분석 페이지", issues)
    page_ids = _require_unique_ids(pages, "pageId", "PAGE_IDS_INVALID", "설계 페이지", issues)
    design_ids = _require_unique_ids(designs, "pageId", "DESIGN_PAGE_IDS_INVALID", "페이지 설계", issues)
    if page_ids != analysis_ids:
        issues.append(issue("PAGE_INVENTORY_ANALYSIS_MISMATCH", "설계 페이지 목록은 분석에서 발견·요구된 전체 페이지와 정확히 일치해야 합니다.", analysis=sorted(analysis_ids), designInventory=sorted(page_ids)))
    if design_ids != page_ids or len(designs) != len(page_ids):
        issues.append(issue("FULL_PAGE_MOCKUP_ONE_TO_ONE_REQUIRED", "샘플 몇 개가 아니라 전체 페이지와 설계 장부가 정확히 1:1이어야 합니다.", expected=sorted(page_ids), actual=sorted(design_ids)))
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
            issues.append(issue("PAGE_MOCKUP_FILE_MISSING", "각 페이지별 독립 목업 HTML/SVG 파일이 필요하며 충분한 시각 구조를 포함해야 합니다.", pageId=pid, path=mockup))
            text = ""
        else:
            text = _run_path(run_root, mockup).read_text(encoding="utf-8", errors="replace")
            if pid and pid not in text:
                issues.append(issue("PAGE_MOCKUP_ID_MARKER_MISSING", "목업 파일에 해당 pageId 추적 표식이 없습니다.", pageId=pid, path=mockup))
            if len(re.findall(r"<(?:header|main|section|article|nav|form|footer|div)\b", text, re.I)) < 5:
                issues.append(issue("PAGE_MOCKUP_VISUAL_STRUCTURE_TOO_SHALLOW", "텍스트 계획이 아니라 실제 페이지 레이아웃 구조가 필요합니다.", pageId=pid))
        screenshot_file = _run_path(run_root, screenshot)
        png = _png_info(screenshot_file) if screenshot_file.is_file() else None
        if not png or png[0] < 320 or png[1] < 568 or screenshot_file.stat().st_size < 1000:
            issues.append(issue("PAGE_MOCKUP_SCREENSHOT_INVALID", "각 페이지별 실제 PNG 시각 증거가 필요하며 최소 320x568/1KB여야 합니다.", pageId=pid, path=screenshot, dimensions=png))
        else:
            if page.get("screenshotSha256") != sha256_file(screenshot_file):
                issues.append(issue("PAGE_MOCKUP_SCREENSHOT_HASH_MISMATCH", "목업 PNG의 현재 SHA-256이 설계 장부와 일치하지 않습니다.", pageId=pid))
        mockup_file = _run_path(run_root, mockup)
        if mockup_file.is_file() and page.get("mockupSha256") != sha256_file(mockup_file):
            issues.append(issue("PAGE_MOCKUP_FILE_HASH_MISMATCH", "목업 HTML/SVG의 현재 SHA-256이 설계 장부와 일치하지 않습니다.", pageId=pid))
        research_ids = unique_nonempty(page.get("researchSourceIds", []))
        research_types = {str(source_by_id.get(value, {}).get("sourceType", "")) for value in research_ids if value in source_by_id}
        if len(research_ids) < 4 or any(value not in source_by_id for value in research_ids) or "github" not in research_types or not research_types.intersection({"web", "official"}):
            issues.append(issue("DESIGN_RESEARCH_TRACE_INSUFFICIENT", "각 페이지 설계는 유효한 본문 출처 4개 이상(웹/공식 + GitHub 포함)과 연결되어야 합니다.", pageId=pid, sourceIds=research_ids))
        for field in ["layoutRationale", "visualHierarchy", "typographyStrategy", "colorStrategy", "smallBusinessAttentionStrategy", "conversionStrategy", "accessibilityStrategy"]:
            if len(str(page.get(field, "")).strip()) < 40:
                issues.append(issue("PAGE_DESIGN_FIELD_INSUFFICIENT", f"페이지별 {field} 근거가 40자 이상으로 구체적이어야 합니다.", pageId=pid, field=field))
        expected_regions = set(unique_nonempty(page_spec.get("requiredRegions", [])))
        designed_regions = set(unique_nonempty(page.get("regionIds", [])))
        if designed_regions != expected_regions:
            issues.append(issue("PAGE_REGION_COVERAGE_INCOMPLETE", "목업 영역이 분석 페이지의 requiredRegions와 정확히 일치해야 합니다.", pageId=pid, expected=sorted(expected_regions), actual=sorted(designed_regions)))
        for region in expected_regions:
            if text and region not in text:
                issues.append(issue("MOCKUP_REGION_MARKER_MISSING", "목업 실제 파일에 영역 ID 표식이 없습니다.", pageId=pid, regionId=region))
        for key, code in [("fieldIds", "PAGE_FIELD_DESIGN_COVERAGE_INCOMPLETE"), ("logicIds", "PAGE_LOGIC_DESIGN_COVERAGE_INCOMPLETE"), ("featureIds", "PAGE_FEATURE_DESIGN_COVERAGE_INCOMPLETE")]:
            expected_values = set(unique_nonempty(page_spec.get(key, [])))
            actual_values = set(unique_nonempty(page.get(key, [])))
            if actual_values != expected_values:
                issues.append(issue(code, "페이지 설계 추적 ID가 분석 장부와 정확히 일치하지 않습니다.", pageId=pid, field=key, expected=sorted(expected_values), actual=sorted(actual_values)))
            missing_markers = [value for value in expected_values if text and value not in text]
            if missing_markers:
                issues.append(issue(f"{code}_MOCKUP_MARKER_MISSING", "목업 실제 파일에 필드/로직/기능 추적 ID가 없습니다.", pageId=pid, field=key, missing=missing_markers))
        expected_states = set(unique_nonempty(page_spec.get("states", [])))
        actual_states = {str(item.get("name", item)) if isinstance(item, dict) else str(item) for item in page.get("states", [])}
        if not expected_states.issubset(actual_states) or "default" not in actual_states:
            issues.append(issue("PAGE_STATE_DESIGN_COVERAGE_INCOMPLETE", "기본·로딩·빈값·오류 등 분석된 상태를 목업에 포함해야 합니다.", pageId=pid, expected=sorted(expected_states), actual=sorted(actual_states)))
        image_strategy = page.get("imageStrategy", {})
        motion_strategy = page.get("motionStrategy", {})
        visibility = str(page_spec.get("visibility", "public")).lower()
        if not isinstance(image_strategy, dict) or "required" not in image_strategy or len(str(image_strategy.get("reason", ""))) < 30:
            issues.append(issue("IMAGE_DECISION_MISSING", "각 페이지마다 이미지 사용 여부와 프로젝트별 이유가 필요합니다.", pageId=pid))
        elif visibility in PUBLIC_VISIBILITIES and image_strategy.get("required") is not True:
            exception = str(image_strategy.get("engagementException", ""))
            if len(exception) < 60:
                issues.append(issue("PUBLIC_PAGE_IMAGE_REQUIRED", "사용자 대상 페이지에는 의미 있는 이미지가 필요하며, 제외하려면 60자 이상의 구체적 예외 근거가 필요합니다.", pageId=pid, visibility=visibility))
        elif image_strategy.get("required") and not image_strategy.get("slots"):
            issues.append(issue("IMAGE_SLOT_PLAN_MISSING", "이미지가 필요한 페이지에는 구체적 슬롯·목적·비율 계획이 필요합니다.", pageId=pid))
        elif image_strategy.get("required"):
            for slot in image_strategy.get("slots", []):
                if not isinstance(slot, dict) or not all(nonempty(slot.get(field)) for field in ["slotId", "purpose", "aspectRatio", "sourceStrategy"]):
                    issues.append(issue("IMAGE_SLOT_PLAN_INCOMPLETE", "각 이미지 슬롯에는 slotId/purpose/aspectRatio/sourceStrategy가 필요합니다.", pageId=pid, slot=slot))
        if not isinstance(motion_strategy, dict) or "required" not in motion_strategy or len(str(motion_strategy.get("reason", ""))) < 30:
            issues.append(issue("MOTION_DECISION_MISSING", "각 페이지마다 모션 사용 여부와 프로젝트별 이유가 필요합니다.", pageId=pid))
        elif visibility not in STATIC_EXCEPTION_VISIBILITIES and motion_strategy.get("required") is not True:
            exception = str(motion_strategy.get("engagementException", ""))
            if len(exception) < 60:
                issues.append(issue("USER_PAGE_MOTION_REQUIRED", "사용자 경험 페이지에는 목적성 모션이 필요하며, 제외하려면 60자 이상의 접근성·성능 근거가 필요합니다.", pageId=pid, visibility=visibility))
        elif motion_strategy.get("required") and (not motion_strategy.get("motions") or len(str(motion_strategy.get("reducedMotionPlan", ""))) < 20):
            issues.append(issue("MOTION_STORYBOARD_MISSING", "모션이 필요한 페이지에는 trigger/from/to/duration/easing/purpose와 reduced-motion 계획이 필요합니다.", pageId=pid))
        elif motion_strategy.get("required"):
            for motion in motion_strategy.get("motions", []):
                if not isinstance(motion, dict) or not all(nonempty(motion.get(field)) for field in ["motionId", "trigger", "from", "to", "duration", "easing", "purpose"]):
                    issues.append(issue("MOTION_STORYBOARD_INCOMPLETE", "각 모션에는 motionId/trigger/from/to/duration/easing/purpose가 필요합니다.", pageId=pid, motion=motion))
    if len(mockup_paths) != len(set(mockup_paths)) or len(screenshot_paths) != len(set(screenshot_paths)) or any(not value for value in mockup_paths + screenshot_paths):
        issues.append(issue("REPRESENTATIVE_SAMPLE_REUSE_FORBIDDEN", "하나의 샘플 목업/스크린샷을 여러 페이지에 재사용할 수 없습니다."))
    board = ledger.get("visualStructureBoard", {})
    board_image = _run_path(run_root, str(board.get("imagePath", "")))
    board_html = _run_path(run_root, str(board.get("htmlPath", "")))
    if not _file_ok(run_root, str(board.get("htmlPath", "")), 800) or not _png_info(board_image) or board_image.stat().st_size < 1000:
        issues.append(issue("VISUAL_STRUCTURE_BOARD_MISSING", "전체 페이지를 한눈에 비교하는 보드 HTML과 PNG가 필요합니다."))
    else:
        if board.get("htmlSha256") != sha256_file(board_html) or board.get("imageSha256") != sha256_file(board_image):
            issues.append(issue("VISUAL_STRUCTURE_BOARD_HASH_MISMATCH", "전체 페이지 보드 HTML/PNG 해시가 장부와 일치하지 않습니다."))
    if set(unique_nonempty(board.get("pageIds", []))) != page_ids:
        issues.append(issue("VISUAL_BOARD_PAGE_COVERAGE_INCOMPLETE", "전체 페이지 보드가 pageInventory 전부를 포함하지 않습니다."))
    for field in ["smallBusinessAttentionStrategy", "imageSystem", "motionSystem", "accessibilitySystem", "conversionSystem", "performanceBudget"]:
        if not nonempty(ledger.get("globalQuality", {}).get(field)):
            issues.append(issue("GLOBAL_DESIGN_QUALITY_FIELD_MISSING", "전역 디자인 품질 계약이 비어 있습니다.", field=field))
    _require_no_omissions(inventory, issues, "페이지 목록")
    _require_no_omissions(ledger, issues, "설계 장부")
    return issues


def gate_implement(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    pages = (_read_required_json(run_root / "design" / "page-inventory.json", issues, "PAGE_INVENTORY_MISSING") or {}).get("pages", [])
    design_pages = (_read_required_json(run_root / "design" / "design-ledger.json", issues, "DESIGN_LEDGER_MISSING") or {}).get("pages", [])
    ledger = _read_required_json(run_root / "implementation" / "implementation-ledger.json", issues, "IMPLEMENTATION_LEDGER_MISSING") or {}
    forbidden = scan_forbidden_manual_keys(ledger)
    if forbidden:
        issues.append(issue("MANUAL_DESIGN_SELECTION_FORBIDDEN", "구현 장부에 수동 컨셉/색상 선택이 남아 있습니다.", paths=forbidden))
    impl_pages = ledger.get("pages", []) if isinstance(ledger, dict) else []
    expected = _require_unique_ids(pages, "pageId", "PAGE_IDS_INVALID", "페이지", issues)
    actual = _require_unique_ids(impl_pages, "pageId", "IMPLEMENTATION_PAGE_IDS_INVALID", "구현 페이지", issues)
    if expected != actual or len(impl_pages) != len(expected):
        issues.append(issue("IMPLEMENTATION_PAGE_COVERAGE_INCOMPLETE", "전체 페이지 구현 장부가 pageInventory와 정확히 1:1이어야 합니다.", expected=sorted(expected), actual=sorted(actual)))
    project_root = Path(str(state.get("projectRoot", "")))
    design_by_id = {str(item.get("pageId", "")): item for item in design_pages if isinstance(item, dict)}
    page_by_id = {str(item.get("pageId", "")): item for item in pages if isinstance(item, dict)}
    image_assets = {str(item.get("imageId", "")): item for item in ledger.get("imageAssets", []) if isinstance(item, dict)}
    motions = {str(item.get("motionId", "")): item for item in ledger.get("motionImplementations", []) if isinstance(item, dict)}
    _require_unique_ids(list(image_assets.values()), "imageId", "IMAGE_IDS_INVALID", "이미지", issues) if image_assets else None
    _require_unique_ids(list(motions.values()), "motionId", "MOTION_IDS_INVALID", "모션", issues) if motions else None
    for page in impl_pages:
        if not isinstance(page, dict):
            continue
        pid = str(page.get("pageId", ""))
        files = [safe_resolve(value, project_root) for value in page.get("targetFiles", []) if str(value).strip()]
        if not files or any(not file.is_file() or not is_inside(file, project_root) for file in files):
            issues.append(issue("IMPLEMENTATION_TARGET_FILES_MISSING", "페이지별 실제 구현 파일이 프로젝트 내부에 존재해야 합니다.", pageId=pid, files=[f.as_posix() for f in files]))
        hashes = page.get("fileHashes", {})
        combined_text = ""
        for file in files:
            if not file.is_file() or not is_inside(file, project_root):
                continue
            rel = file.relative_to(project_root).as_posix()
            if hashes.get(rel) != sha256_file(file):
                issues.append(issue("IMPLEMENTATION_FILE_HASH_MISSING", "구현 파일의 현재 SHA-256 증거가 없습니다.", pageId=pid, file=rel))
            if file.suffix.lower() in {".html", ".css", ".js", ".mjs", ".ts", ".tsx", ".jsx", ".kt", ".java", ".xml", ".py", ".dart", ".vue", ".svelte"}:
                combined_text += "\n" + file.read_text(encoding="utf-8", errors="replace")
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
                issues.append(issue(code, "분석·목업과 실제 구현의 추적 ID가 정확히 일치하지 않습니다.", pageId=pid, expected=sorted(expected_ids), actual=sorted(actual_ids)))
            missing_markers = [value for value in expected_ids if not _marker_has_executable_context(combined_text, value)]
            if missing_markers:
                issues.append(issue(f"{code}_CODE_MARKER_MISSING", "구현 장부 ID가 주석이 아닌 실제 실행/마크업 코드에 나타나지 않습니다.", pageId=pid, missing=missing_markers))
        image_ids = set(unique_nonempty(page.get("imageAssetIds", [])))
        motion_ids = set(unique_nonempty(page.get("motionIds", [])))
        if design.get("imageStrategy", {}).get("required") and not image_ids:
            issues.append(issue("PLANNED_IMAGES_NOT_BOUND", "이미지 계획이 실제 구현 자산과 연결되지 않았습니다.", pageId=pid))
        if design.get("motionStrategy", {}).get("required") and not motion_ids:
            issues.append(issue("PLANNED_MOTION_NOT_IMPLEMENTED", "모션 계획이 실제 구현 코드와 연결되지 않았습니다.", pageId=pid))
        unknown_images = sorted(image_ids - set(image_assets))
        unknown_motions = sorted(motion_ids - set(motions))
        if unknown_images:
            issues.append(issue("PAGE_IMAGE_LINK_INVALID", "페이지가 존재하지 않는 imageId를 참조합니다.", pageId=pid, unknown=unknown_images))
        if unknown_motions:
            issues.append(issue("PAGE_MOTION_LINK_INVALID", "페이지가 존재하지 않는 motionId를 참조합니다.", pageId=pid, unknown=unknown_motions))
    for image_id, asset in image_assets.items():
        path = safe_resolve(asset.get("assetPath", ""), project_root)
        if not path.is_file() or not is_inside(path, project_root) or path.stat().st_size < 500:
            issues.append(issue("IMAGE_ASSET_MISSING", "이미지 자산 파일이 실제 프로젝트에 없습니다.", imageId=image_id, path=path.as_posix()))
            continue
        if asset.get("sha256") != sha256_file(path):
            issues.append(issue("IMAGE_ASSET_HASH_MISMATCH", "이미지 자산 현재 해시가 장부와 다릅니다.", imageId=image_id))
        if len(str(asset.get("sourceOrPrompt", ""))) < 20 or len(str(asset.get("licenseOrOwnership", ""))) < 10 or len(str(asset.get("projectFitReason", ""))) < 30:
            issues.append(issue("IMAGE_PROVENANCE_MISSING", "이미지 프롬프트/출처·권리·프로젝트 적합 이유가 필요합니다.", imageId=image_id))
        usages = unique_nonempty(asset.get("usageLocations", []))
        if not usages:
            issues.append(issue("IMAGE_USAGE_LOCATION_MISSING", "이미지 자산 사용 위치가 기록되지 않았습니다.", imageId=image_id))
        else:
            rel_asset = path.relative_to(project_root).as_posix()
            for usage in usages:
                usage_file = safe_resolve(usage, project_root)
                text = usage_file.read_text(encoding="utf-8", errors="replace") if usage_file.is_file() else ""
                if rel_asset not in text and path.name not in text:
                    issues.append(issue("IMAGE_NOT_REFERENCED_BY_CODE", "이미지 자산이 기록된 실제 코드에서 참조되지 않습니다.", imageId=image_id, usage=usage))
    for motion_id, motion in motions.items():
        file = safe_resolve(motion.get("targetFile", ""), project_root)
        text = file.read_text(encoding="utf-8", errors="replace") if file.is_file() and is_inside(file, project_root) else ""
        marker = str(motion.get("implementationMarker", ""))
        reduced = str(motion.get("reducedMotionMarker", ""))
        if not _marker_has_executable_context(text, marker):
            issues.append(issue("MOTION_CODE_MARKER_MISSING", "모션 장부의 구현 표식이 주석이 아닌 실제 코드에 없습니다.", motionId=motion_id, file=file.as_posix()))
        if not reduced or reduced not in text:
            issues.append(issue("REDUCED_MOTION_CODE_MISSING", "접근성을 위한 reduced-motion 실제 코드 증거가 없습니다.", motionId=motion_id, file=file.as_posix()))
        for field in ["trigger", "purpose", "duration", "easing"]:
            if not nonempty(motion.get(field)):
                issues.append(issue("MOTION_SPEC_INCOMPLETE", "모션 구현 장부에 trigger/purpose/duration/easing이 모두 필요합니다.", motionId=motion_id, field=field))
    blocking = [item for item in ledger.get("unresolvedIssues", []) if isinstance(item, dict) and item.get("severity") in {"critical", "major"} and item.get("status") != "resolved"]
    if blocking:
        issues.append(issue("BLOCKING_IMPLEMENTATION_ISSUES_REMAIN", "중대 구현 문제가 해결되지 않았습니다.", count=len(blocking)))
    test_items = ledger.get("tests", [])
    if not test_items:
        issues.append(issue("IMPLEMENTATION_TEST_MAP_MISSING", "페이지·필드·로직·기능별 실제 테스트 파일 매핑이 필요합니다."))
    else:
        _require_unique_ids(test_items, "testId", "IMPLEMENTATION_TEST_IDS_INVALID", "구현 테스트", issues)
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
                issues.append(issue("IMPLEMENTATION_TEST_FILE_MISSING", "구현 테스트 매핑의 실제 테스트 파일이 없습니다.", testId=test_id, file=test_file.as_posix()))
                continue
            if test.get("sha256") != sha256_file(test_file):
                issues.append(issue("IMPLEMENTATION_TEST_FILE_HASH_MISMATCH", "테스트 파일 SHA-256이 장부와 일치하지 않습니다.", testId=test_id))
            marker = str(test.get("testMarker", ""))
            text = test_file.read_text(encoding="utf-8", errors="replace")
            if not _marker_has_executable_context(text, marker):
                issues.append(issue("IMPLEMENTATION_TEST_MARKER_MISSING", "테스트 표식이 실제 테스트 코드에 없습니다.", testId=test_id, marker=marker))
            target_ids = set(unique_nonempty(test.get("targetIds", [])))
            if not target_ids or not target_ids.issubset(all_trace_ids):
                issues.append(issue("IMPLEMENTATION_TEST_TARGET_INVALID", "테스트 targetIds가 실제 페이지/영역/필드/로직/기능 ID와 연결되지 않았습니다.", testId=test_id, targets=sorted(target_ids)))
            covered_ids.update(target_ids)
        missing_test_coverage = sorted(value for value in all_trace_ids if value and value not in covered_ids)
        if missing_test_coverage:
            issues.append(issue("IMPLEMENTATION_TEST_COVERAGE_INCOMPLETE", "모든 페이지·영역·필드·로직·기능 ID가 실제 테스트 파일과 연결되어야 합니다.", missing=missing_test_coverage))
    _require_no_omissions(ledger, issues, "구현 장부")
    return issues


def gate_review(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    pages = (_read_required_json(run_root / "design" / "page-inventory.json", issues, "PAGE_INVENTORY_MISSING") or {}).get("pages", [])
    review = _read_required_json(run_root / "review" / "review.json", issues, "REVIEW_MISSING") or {}
    expected = _require_unique_ids(pages, "pageId", "PAGE_IDS_INVALID", "페이지", issues)
    reviewed = review.get("pages", []) if isinstance(review, dict) else []
    actual = _require_unique_ids(reviewed, "pageId", "REVIEW_PAGE_IDS_INVALID", "리뷰 페이지", issues)
    if expected != actual or len(reviewed) != len(expected):
        issues.append(issue("REVIEW_PAGE_COVERAGE_INCOMPLETE", "실제 구현 후 리뷰가 전체 페이지를 정확히 1:1 포함해야 합니다.", expected=sorted(expected), actual=sorted(actual)))
    required_checks = ["structureMatched", "fieldsMatched", "logicMatched", "featuresMatched", "imagesMatched", "motionMatched", "statesMatched", "overlapFree", "responsivePass", "accessibilityPass"]
    test_report = read_json(run_root / "test" / "test-report.json", {})
    execution_map = {str(item.get("executionId")): item for item in test_report.get("toolExecutions", []) if isinstance(item, dict)}
    implement_gate_path = run_root / "reports" / "gate-implement.json"
    implement_gate = read_json(implement_gate_path, {})
    if implement_gate.get("pass") is not True:
        issues.append(issue("IMPLEMENTATION_GATE_EVIDENCE_MISSING", "리뷰 비교 전에 구현 게이트 통과 증거가 필요합니다."))
    for item in reviewed:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("pageId", ""))
        screenshot = _run_path(run_root, str(item.get("actualScreenshotPath", "")))
        dimensions = _png_info(screenshot) if screenshot.is_file() else None
        if not dimensions or dimensions[0] < 320 or dimensions[1] < 568 or screenshot.stat().st_size < 1000:
            issues.append(issue("ACTUAL_SCREENSHOT_INVALID", "각 전체 페이지의 실제 실행 PNG 스크린샷이 필요합니다.", pageId=pid, dimensions=dimensions))
        elif item.get("actualScreenshotSha256") != sha256_file(screenshot):
            issues.append(issue("ACTUAL_SCREENSHOT_HASH_MISMATCH", "실제 스크린샷 해시가 장부와 일치하지 않습니다.", pageId=pid))
        if not _file_ok(run_root, str(item.get("mockupPath", "")), 800):
            issues.append(issue("REVIEW_MOCKUP_LINK_MISSING", "리뷰가 해당 페이지 목업 파일과 연결되지 않았습니다.", pageId=pid))
        evidence_path = _run_path(run_root, str(item.get("evidencePath", "")))
        if not evidence_path.is_file() or item.get("evidenceSha256") != sha256_file(evidence_path):
            issues.append(issue("REVIEW_RUNTIME_EVIDENCE_INVALID", "리뷰의 실제 브라우저/스크린샷 테스트 결과 파일과 해시가 필요합니다.", pageId=pid))
        else:
            evidence_text = evidence_path.read_text(encoding="utf-8", errors="replace")
            if screenshot.is_file() and screenshot.as_posix() not in evidence_text and screenshot.relative_to(run_root).as_posix() not in evidence_text:
                issues.append(issue("REVIEW_SCREENSHOT_NOT_BOUND_TO_RUNTIME", "스크린샷이 실제 런타임 도구 결과에 연결되지 않았습니다.", pageId=pid))
        linked_execs = set(unique_nonempty(item.get("toolExecutionIds", [])))
        if not linked_execs or any(execution_map.get(value, {}).get("exitCode") != 0 for value in linked_execs):
            issues.append(issue("REVIEW_TOOL_EXECUTION_LINK_INVALID", "리뷰가 성공한 실제 브라우저/스크린샷 도구 실행 ID와 연결되지 않았습니다.", pageId=pid, executionIds=sorted(linked_execs)))
        if item.get("implementationGatePath") != "reports/gate-implement.json" or item.get("implementationGateSha256") != (sha256_file(implement_gate_path) if implement_gate_path.is_file() else ""):
            issues.append(issue("REVIEW_IMPLEMENTATION_GATE_HASH_INVALID", "리뷰가 통과한 구현 게이트 보고서 해시와 연결되지 않았습니다.", pageId=pid))
        failed = [field for field in required_checks if item.get(field) is not True]
        if failed or item.get("pass") is not True:
            issues.append(issue("PAGE_REVIEW_FAILED", "페이지 리뷰의 모든 비교 항목이 실제 증거로 통과해야 합니다.", pageId=pid, failed=failed))
        if item.get("issues"):
            open_items = [value for value in item.get("issues", []) if not isinstance(value, dict) or value.get("status") != "resolved"]
            if open_items:
                issues.append(issue("PAGE_REVIEW_ISSUES_OPEN", "페이지 리뷰 문제를 실제 수정하고 재검증해야 합니다.", pageId=pid, count=len(open_items)))
    if not review.get("crossPageConsistency"):
        issues.append(issue("CROSS_PAGE_CONSISTENCY_REVIEW_MISSING", "전체 페이지 간 내비게이션·타입·간격·상태·모션 일관성 리뷰가 필요합니다."))
    else:
        for item in review.get("crossPageConsistency", []):
            if not isinstance(item, dict) or item.get("pass") is not True:
                issues.append(issue("CROSS_PAGE_CONSISTENCY_FAILED", "전체 페이지 일관성 검토에 실패 항목이 있습니다.")); continue
            evidence = _run_path(run_root, str(item.get("evidencePath", "")))
            if not evidence.is_file() or item.get("evidenceSha256") != sha256_file(evidence):
                issues.append(issue("CROSS_PAGE_EVIDENCE_INVALID", "전체 페이지 일관성 검토의 실제 도구 증거와 해시가 없습니다."))
            linked = set(unique_nonempty(item.get("toolExecutionIds", [])))
            if not linked or any(execution_map.get(value, {}).get("exitCode") != 0 for value in linked):
                issues.append(issue("CROSS_PAGE_TOOL_LINK_INVALID", "전체 페이지 일관성 검토가 성공한 도구 실행과 연결되지 않았습니다."))
    if review.get("decision") != "approved":
        issues.append(issue("REVIEW_DECISION_NOT_APPROVED", "모든 실제 페이지 리뷰가 통과한 뒤 decision=approved가 필요합니다."))
    blocking = [item for item in review.get("unresolvedIssues", []) if isinstance(item, dict) and item.get("severity") in {"critical", "major"} and item.get("status") != "resolved"]
    if blocking:
        issues.append(issue("BLOCKING_REVIEW_ISSUES_REMAIN", "중대 리뷰 문제가 해결되지 않았습니다.", count=len(blocking)))
    _require_no_omissions(review, issues, "리뷰 장부")
    return issues


def gate_test(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    report = _read_required_json(run_root / "test" / "test-report.json", issues, "TEST_REPORT_MISSING") or {}
    if report.get("apkInstallationPolicy") != "forbidden":
        issues.append(issue("APK_INSTALL_POLICY_NOT_FORBIDDEN", "APK 설치 제외 정책이 test-report에 고정되지 않았습니다."))
    discovery = report.get("toolDiscovery", {})
    discovery_path = _run_path(run_root, str(discovery.get("path", "")))
    if not discovery_path.is_file() or discovery.get("sha256") != sha256_file(discovery_path):
        issues.append(issue("TOOL_DISCOVERY_EVIDENCE_MISSING", "실제 도구 탐지 결과와 SHA-256 증거가 필요합니다."))

    executions = report.get("toolExecutions", []) if isinstance(report, dict) else []
    if not executions:
        issues.append(issue("TOOL_EXECUTIONS_MISSING", "실제 빌드·브라우저·에뮬레이터·시뮬레이터 도구 실행 기록이 없습니다."))
    execution_ids: set[str] = set()
    passed_tool_ids: set[str] = set()
    for execution in executions:
        if not isinstance(execution, dict):
            issues.append(issue("TOOL_EXECUTION_INVALID", "도구 실행 기록은 객체여야 합니다.")); continue
        execution_id = str(execution.get("executionId", ""))
        tool_id = str(execution.get("toolId", ""))
        if not execution_id or execution_id in execution_ids:
            issues.append(issue("TOOL_EXECUTION_ID_INVALID", "도구 실행 ID는 비어 있지 않고 중복되지 않아야 합니다.", executionId=execution_id))
        execution_ids.add(execution_id)
        forbidden = command_forbidden(str(execution.get("command", "")))
        if forbidden:
            issues.append(issue("APK_INSTALL_COMMAND_DETECTED", "APK 설치 또는 자동 설치 경로가 실행 기록에서 발견됐습니다.", executionId=execution_id, pattern=forbidden))
        if execution.get("exitCode") != 0 or execution.get("status") != "passed" or execution.get("timedOut") is True:
            issues.append(issue("TOOL_EXECUTION_FAILED", "필수 도구 실행은 시간초과 없이 종료코드 0이어야 합니다.", executionId=execution_id, toolId=tool_id, exitCode=execution.get("exitCode")))
        else:
            passed_tool_ids.add(tool_id)
            passed_tool_ids.update(str(value) for value in execution.get("satisfiesToolIds", []) if value)
        log_path = _run_path(run_root, str(execution.get("logPath", "")))
        if not log_path.is_file() or not is_inside(log_path, run_root) or log_path.stat().st_size < 1:
            issues.append(issue("TOOL_LOG_MISSING", "도구 실행 로그 파일이 없습니다.", executionId=execution_id))
        elif execution.get("logSha256") != sha256_file(log_path):
            issues.append(issue("TOOL_LOG_HASH_MISMATCH", "도구 로그 SHA-256이 일치하지 않습니다.", executionId=execution_id))
        for artifact in execution.get("artifacts", []):
            if not isinstance(artifact, dict) or artifact.get("missing") is True:
                issues.append(issue("TOOL_ARTIFACT_MISSING", "도구 실행 산출물이 누락됐습니다.", executionId=execution_id, artifact=artifact)); continue
            artifact_path = Path(str(artifact.get("path", "")))
            if artifact.get("directory") is True:
                if not artifact_path.is_dir():
                    issues.append(issue("TOOL_ARTIFACT_DIRECTORY_MISSING", "도구 산출물 디렉터리가 없습니다.", path=artifact_path.as_posix()))
            elif not artifact_path.is_file() or artifact.get("sha256") != sha256_file(artifact_path):
                issues.append(issue("TOOL_ARTIFACT_HASH_MISMATCH", "도구 산출물 파일과 SHA-256이 일치하지 않습니다.", path=artifact_path.as_posix()))

    expected_tools = set(canonical_required_tool_ids(
        str(state.get("targetPipeline", "web-responsive")),
        Path(str(state.get("projectRoot", "."))).resolve(),
    ))
    missing_tools = sorted(expected_tools - passed_tool_ids)
    if missing_tools:
        issues.append(issue("TARGET_TOOLCHAIN_COVERAGE_INCOMPLETE", "대상 플랫폼에 필요한 도구가 실제 성공 실행되지 않았습니다.", expected=sorted(expected_tools), passed=sorted(passed_tool_ids), missing=missing_tools))

    pages = (read_json(run_root / "design" / "page-inventory.json", {}) or {}).get("pages", [])
    expected_pages = {str(item.get("pageId", "")) for item in pages if isinstance(item, dict)}
    checked: set[str] = set()
    for item in report.get("pageVisualChecks", []):
        _physical_evidence_item(run_root, item, execution_ids, "pageVisualChecks", issues)
        if isinstance(item, dict) and item.get("pass") is True:
            checked.add(str(item.get("pageId", "")))
    if checked != expected_pages:
        issues.append(issue("VISUAL_TEST_COVERAGE_INCOMPLETE", "구현 후 시각 테스트가 전체 페이지를 정확히 포함하지 않습니다.", expected=sorted(expected_pages), checked=sorted(checked)))

    for group in ["accessibilityChecks", "responsiveChecks", "securityChecks", "stateChecks", "performanceChecks", "visualRegressionChecks"]:
        values = report.get(group, [])
        if not values:
            issues.append(issue(f"{group.upper()}_INCOMPLETE", f"{group} 실제 도구 증거가 없습니다."))
            continue
        for item in values:
            _physical_evidence_item(run_root, item, execution_ids, group, issues)

    target = str(state.get("targetPipeline", ""))
    if target in {"android-native", "app-mobile-webview", "cross-platform", "ios-native"}:
        checks = report.get("emulatorSimulatorChecks", [])
        if not checks:
            issues.append(issue("EMULATOR_SIMULATOR_EVIDENCE_MISSING", "대상 플랫폼의 에뮬레이터/시뮬레이터 실제 증거가 없습니다."))
        for item in checks:
            _physical_evidence_item(run_root, item, execution_ids, "emulatorSimulatorChecks", issues)

    blocking = [item for item in report.get("unresolvedIssues", []) if isinstance(item, dict) and item.get("severity") in {"critical", "major"} and item.get("status") != "resolved"]
    if blocking:
        issues.append(issue("BLOCKING_TEST_ISSUES_REMAIN", "중대 테스트 문제가 해결되지 않았습니다.", count=len(blocking)))
    if report.get("releaseDecision") != "approved":
        issues.append(issue("RELEASE_DECISION_NOT_APPROVED", "모든 물리 도구 증거 통과 후 releaseDecision=approved가 필요합니다."))
    if state.get("analysisMode") == "analysis-folder-provided":
        snapshot = compare_snapshot(run_root)
        if not snapshot.get("ok"):
            issues.append(issue("ANALYSIS_FOLDER_MUTATED", "최종 테스트 시 분석 원본이 변경되어 있습니다.", **snapshot))
    _require_no_omissions(report, issues, "테스트 보고서")
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


def gate_release(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for stage in STAGES[:-1]:
        if not str(state.get("stageStatus", {}).get(stage, "")).startswith("passed"):
            issues.append(issue("PREVIOUS_STAGE_NOT_PASSED", "release 전에 모든 이전 단계가 통과해야 합니다.", stage=stage, status=state.get("stageStatus", {}).get(stage)))
    release = _read_required_json(run_root / "release" / "release.json", issues, "RELEASE_MANIFEST_MISSING") or {}
    for field in ["version", "artifacts", "installation", "rollback", "privacy", "support", "costLedger", "releaseNotes"]:
        if not nonempty(release.get(field)):
            issues.append(issue("RELEASE_FIELD_MISSING", f"release.json 필수 항목이 없습니다: {field}", field=field))
    for artifact in release.get("artifacts", []):
        if not isinstance(artifact, dict):
            issues.append(issue("RELEASE_ARTIFACT_INVALID", "릴리스 artifacts는 객체 목록이어야 합니다.")); continue
        path = safe_resolve(artifact.get("path", ""), Path(str(state.get("projectRoot", ""))))
        if not path.is_file() or artifact.get("sha256") != sha256_file(path):
            issues.append(issue("RELEASE_ARTIFACT_HASH_MISMATCH", "릴리스 파일과 SHA-256 증거가 일치하지 않습니다.", path=path.as_posix()))
    scan = release.get("securityScan", {})
    if scan.get("status") != "passed" or scan.get("findings"):
        issues.append(issue("RELEASE_SECURITY_SCAN_FAILED", "공개 배포 보안 스캔이 통과하지 않았습니다.", scan=scan))
    open_tickets = _open_repair_tickets(run_root)
    if open_tickets:
        issues.append(issue("OPEN_REPAIR_TICKETS_REMAIN", "열린 자동수리 티켓이 남아 있습니다.", tickets=open_tickets))
    if release.get("openRepairTickets"):
        issues.append(issue("RELEASE_LEDGER_OPEN_TICKETS_REMAIN", "release.json의 openRepairTickets가 비어 있어야 합니다."))
    if state.get("analysisMode") == "analysis-folder-provided":
        snapshot = compare_snapshot(run_root)
        if not snapshot.get("ok"):
            issues.append(issue("ANALYSIS_FOLDER_MUTATED", "릴리스 시 분석 원본이 변경되어 있습니다.", **snapshot))
    _require_no_omissions(release, issues, "릴리스 장부")
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
    if enforce_order:
        previous_ok, missing = _all_previous_passed(state, stage)
        if not previous_ok:
            issues.append(issue("STAGE_ORDER_VIOLATION", "이전 단계가 통과하기 전에는 현재 단계를 통과할 수 없습니다.", requestedStage=stage, missingStages=missing))
    issues.extend(GATE_FUNCTIONS[stage](run_root, state))
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
