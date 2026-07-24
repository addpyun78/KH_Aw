from __future__ import annotations

from pathlib import Path
from typing import Any

from .capabilities import capability_policy
from .tooling import tool_policy
from .orchestration import orchestration_policy
from .util import exact_instruction_lines, utc_now, write_json

STAGES = ["intake", "analyze", "research", "design", "implement", "review", "test", "release"]
RESEARCH_CATEGORIES = [
    "competitor", "feature", "design-system", "image", "font", "icon",
    "motion", "accessibility", "platform", "conversion",
]
FORBIDDEN_MANUAL_KEYS = {
    "manualConcept", "manualConceptSelection", "selectedConcept", "selectedTemplate",
    "manualColor", "manualColorSelection", "selectedColors", "selectedPalette",
    "conceptPicker", "colorPicker", "userSelectedConcept", "userSelectedColors",
    "templatePicker", "themePicker", "fixedDesignPreset", "presetPalette",
}


def requirement_contract(instructions: str) -> dict[str, Any]:
    lines = exact_instruction_lines(instructions)
    requirements = []
    raw_coverage = []
    for index, line in enumerate(lines, 1):
        raw_id = f"RAW-{index:03d}"
        req_id = f"REQ-{index:03d}"
        requirements.append({
            "id": req_id,
            "requirement": line,
            "source": raw_id,
            "priority": "critical",
            "status": "preserved",
            "acceptanceChecks": [],
        })
        raw_coverage.append({
            "id": raw_id,
            "lineNumber": index,
            "sourceText": line,
            "requirementIds": [req_id],
            "status": "preserved",
            "evidence": "Exact non-empty instruction line preserved at initialization.",
        })
    return {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "rawInstructionCount": len(lines),
        "requirements": requirements,
        "rawInstructionCoverage": raw_coverage,
        "omissions": [],
    }


def analysis_ledger_template() -> dict[str, Any]:
    return {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "analysisFolderMode": "",
        "projectKind": "",
        "greenfieldJustification": "",
        "projectSummary": "",
        "projectStructure": {"fileCount": 0, "directoryCount": 0, "keyPaths": []},
        "techStack": [],
        "architecture": {"current": "", "problems": [], "upgradeDirection": ""},
        "requirementCoverage": [],
        "pageInventory": [],
        "fieldInventory": [],
        "logicInventory": [],
        "featureInventory": [],
        "fileFindings": [],
        "logicFindings": [],
        "securityFindings": [],
        "performanceFindings": [],
        "designFindings": [],
        "strengths": [],
        "weaknesses": [],
        "risks": [],
        "upgradeTargets": [],
        "analysisFolderEvidence": {},
        "omissions": [],
    }


def research_plan_template(requirements: dict[str, Any], target: str) -> dict[str, Any]:
    reqs = requirements.get("requirements", []) if isinstance(requirements, dict) else []
    linked = [item.get("id") for item in reqs if isinstance(item, dict) and item.get("id")]
    elements = []
    for index, category in enumerate(RESEARCH_CATEGORIES, 1):
        elements.append({
            "id": f"BASE-{index:02d}-{category.upper()}",
            "label": "AI가 현재 프로젝트 요구사항과 분석 결과에서 동적으로 작성해야 함",
            "category": category,
            "requirementIds": linked,
            "reason": f"{category} 영역의 프로젝트 적합 근거 확보",
            "targetPipeline": target,
            "exceptionCode": "",
            "webQueries": [],
            "githubQueries": [],
            "status": "AI_MUST_REPLACE_DYNAMICALLY",
        })
    return {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "targetPipeline": target,
        "projectLabel": "AI가 분석 결과에서 동적으로 작성",
        "rules": {
            "bodyExtractionRequired": True,
            "webSourcesPerElement": 2,
            "githubSourcesPerElement": 2,
            "searchResultPageIsNotEvidence": True,
            "manualConceptSelectionForbidden": True,
            "manualColorSelectionForbidden": True,
            "fixedDesignPresetForbidden": True,
        },
        "elements": elements,
    }


def page_inventory_template() -> dict[str, Any]:
    return {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "pages": [],
        "rule": "분석에서 발견·요구된 모든 실제 페이지를 빠짐없이 등록하며 대표 샘플로 대체하지 않는다.",
    }


def design_ledger_template() -> dict[str, Any]:
    return {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "designOriginPolicy": {
            "mode": "dynamic-web-body-research",
            "manualConceptSelection": False,
            "manualColorSelection": False,
            "fixedDesignPreset": False,
            "projectSpecificEveryRun": True,
        },
        "visualStructureBoard": {"htmlPath": "", "imagePath": "", "pageIds": []},
        "pages": [],
        "globalQuality": {
            "smallBusinessAttentionStrategy": "",
            "imageSystem": "",
            "motionSystem": "",
            "accessibilitySystem": "",
            "conversionSystem": "",
            "performanceBudget": {},
        },
        "omissions": [],
    }


def implementation_ledger_template() -> dict[str, Any]:
    return {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "pages": [],
        "imageAssets": [],
        "motionImplementations": [],
        "dataImplementations": [],
        "tests": [],
        "unresolvedIssues": [],
        "omissions": [],
    }


def review_template() -> dict[str, Any]:
    return {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "pages": [],
        "crossPageConsistency": [],
        "unresolvedIssues": [],
        "decision": "pending",
        "omissions": [],
    }


def test_template() -> dict[str, Any]:
    return {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "apkInstallationPolicy": "forbidden",
        "toolDiscovery": {},
        "toolExecutions": [],
        "commands": [],
        "pageVisualChecks": [],
        "accessibilityChecks": [],
        "responsiveChecks": [],
        "securityChecks": [],
        "stateChecks": [],
        "performanceChecks": [],
        "visualRegressionChecks": [],
        "emulatorSimulatorChecks": [],
        "unresolvedIssues": [],
        "releaseDecision": "pending",
        "omissions": [],
    }


def release_template() -> dict[str, Any]:
    return {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "version": "",
        "artifacts": [],
        "installation": "",
        "rollback": "",
        "privacy": "",
        "support": "",
        "costLedger": [],
        "securityScan": {"status": "pending", "scannedRoot": "", "findings": []},
        "openRepairTickets": [],
        "releaseNotes": "",
        "omissions": [],
    }


def create_run_contracts(run_root: Path, instructions: str, target: str) -> dict[str, str]:
    folders = {
        "contract": run_root / "contract",
        "analysis": run_root / "analysis",
        "evidence": run_root / "evidence",
        "design": run_root / "design",
        "implementation": run_root / "implementation",
        "review": run_root / "review",
        "test": run_root / "test",
        "release": run_root / "release",
        "repairs": run_root / "repairs",
        "reports": run_root / "reports",
        "checkpoints": run_root / "checkpoints",
        "events": run_root / "events",
        "orchestration": run_root / "orchestration",
    }
    for folder in folders.values():
        folder.mkdir(parents=True, exist_ok=True)
    (folders["design"] / "mockups").mkdir(parents=True, exist_ok=True)
    (folders["design"] / "screenshots").mkdir(parents=True, exist_ok=True)
    (folders["review"] / "screenshots").mkdir(parents=True, exist_ok=True)
    (folders["test"] / "logs").mkdir(parents=True, exist_ok=True)

    requirements = requirement_contract(instructions)
    write_json(folders["contract"] / "requirements.json", requirements)
    write_json(folders["contract"] / "native-capability-policy.json", capability_policy())
    write_json(folders["contract"] / "tool-policy.json", tool_policy(target))
    write_json(folders["contract"] / "subagent-orchestration-policy.json", orchestration_policy())
    write_json(folders["analysis"] / "analysis-ledger.json", analysis_ledger_template())
    write_json(folders["evidence"] / "research-plan.json", research_plan_template(requirements, target))
    write_json(folders["evidence"] / "source-registry.json", {"schemaVersion": "3.0", "sources": []})
    write_json(folders["design"] / "page-inventory.json", page_inventory_template())
    write_json(folders["design"] / "design-ledger.json", design_ledger_template())
    write_json(folders["implementation"] / "implementation-ledger.json", implementation_ledger_template())
    write_json(folders["review"] / "review.json", review_template())
    write_json(folders["test"] / "test-report.json", test_template())
    write_json(folders["release"] / "release.json", release_template())

    return {
        "requirements": (folders["contract"] / "requirements.json").as_posix(),
        "nativeCapabilityPolicy": (folders["contract"] / "native-capability-policy.json").as_posix(),
        "toolPolicy": (folders["contract"] / "tool-policy.json").as_posix(),
        "subagentOrchestrationPolicy": (folders["contract"] / "subagent-orchestration-policy.json").as_posix(),
        "analysisLedger": (folders["analysis"] / "analysis-ledger.json").as_posix(),
        "researchPlan": (folders["evidence"] / "research-plan.json").as_posix(),
        "sourceRegistry": (folders["evidence"] / "source-registry.json").as_posix(),
        "pageInventory": (folders["design"] / "page-inventory.json").as_posix(),
        "designLedger": (folders["design"] / "design-ledger.json").as_posix(),
        "implementationLedger": (folders["implementation"] / "implementation-ledger.json").as_posix(),
        "review": (folders["review"] / "review.json").as_posix(),
        "testReport": (folders["test"] / "test-report.json").as_posix(),
        "release": (folders["release"] / "release.json").as_posix(),
    }


def scan_forbidden_manual_keys(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_MANUAL_KEYS:
                hits.append(child_path)
            hits.extend(scan_forbidden_manual_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(scan_forbidden_manual_keys(child, f"{path}[{index}]"))
    return hits


def remove_forbidden_manual_keys(value: Any) -> tuple[Any, list[str]]:
    removed: list[str] = []
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, child in value.items():
            if key in FORBIDDEN_MANUAL_KEYS:
                removed.append(key)
                continue
            new_child, child_removed = remove_forbidden_manual_keys(child)
            cleaned[key] = new_child
            removed.extend(child_removed)
        return cleaned, removed
    if isinstance(value, list):
        cleaned_list = []
        for child in value:
            new_child, child_removed = remove_forbidden_manual_keys(child)
            cleaned_list.append(new_child)
            removed.extend(child_removed)
        return cleaned_list, removed
    return value, removed
