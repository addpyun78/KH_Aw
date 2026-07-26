from __future__ import annotations

from pathlib import Path
from typing import Any

from .capabilities import capability_policy
from .language_policy import language_policy
from .tooling import tool_policy
from .orchestration import orchestration_policy
from .util import exact_instruction_lines, utc_now, write_json
from .requirement_compiler import compile_requirements
from .task_graph import build_task_graph

STAGES = ["intake", "analyze", "research", "design", "implement", "review", "test", "release"]
PASSED_STAGE_STATUSES = {
    "passed",
    "passed-after-deterministic-repair",
    "passed-final-verification",
}
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


def stage_status_passed(value: Any) -> bool:
    return str(value) in PASSED_STAGE_STATUSES


def requirement_contract(instructions: str) -> dict[str, Any]:
    return compile_requirements(instructions)


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
            "label": "AI must replace this placeholder from current project requirements and analysis.",
            "category": category,
            "requirementIds": linked,
            "reason": f"Collect project-specific evidence for the {category} area.",
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
        "projectLabel": "AI must derive this dynamically from the analysis.",
        "rules": {
            "bodyExtractionRequired": True,
            "webSourcesPerElement": 2,
            "githubSourcesPerElement": 2,
            "searchResultPageIsNotEvidence": True,
            "manualConceptSelectionForbidden": True,
            "manualColorSelectionForbidden": True,
            "fixedDesignPresetForbidden": True,
        },
        "requirementCoverage": [],
        "elements": elements,
    }


def page_inventory_template() -> dict[str, Any]:
    return {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "candidateInventoryPath": "inventory/page-candidates.json",
        "pages": [],
        "excludedCandidates": [],
        "rule": "Register every real page discovered or required by analysis. A representative sample cannot replace full page coverage.",
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
        "requirementCoverage": [],
        "globalQuality": {
            "smallBusinessAttentionStrategy": "",
            "imageSystem": "",
            "heroSystem": "",
            "iconSystem": "",
            "fontSystem": "",
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
        "requirementCoverage": [],
        "imageAssets": [],
        "motionImplementations": [],
        "dataImplementations": [],
        "tests": [],
        "unresolvedIssues": [],
        "omissions": [],
    }


def copy_audit_template() -> dict[str, Any]:
    return {
        "schemaVersion": "3.2",
        "generatedAt": utc_now(),
        "targetPipeline": "",
        "analysisRoot": "",
        "productRoot": "",
        "sourceFileCount": 0,
        "productFileCount": 0,
        "copiedFileCount": 0,
        "forbiddenCopyCount": 0,
        "nativeForbiddenCopyCount": 0,
        "copiedFiles": [],
        "omissions": [],
    }


def session_forensics_template() -> dict[str, Any]:
    return {
        "schemaVersion": "3.2",
        "generatedAt": utc_now(),
        "sessionId": "",
        "commands": [],
        "failedCommands": [],
        "notRunRequiredChecks": [],
        "finalReportClaims": [],
        "evidenceMismatches": [],
        "slashCapabilityFindings": [],
        "completionTruth": "not-evaluated",
        "omissions": [],
    }


def review_template() -> dict[str, Any]:
    return {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "pages": [],
        "requirementCoverage": [],
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
        "requirementCoverage": [],
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
        "requirementCoverage": [],
        "artifacts": [],
        "installation": "",
        "rollback": "",
        "privacy": "",
        "support": "",
        "costLedger": [],
        "securityScan": {"status": "pending", "scannedRoot": "", "findings": []},
        "openRepairTickets": [],
        "releaseNotes": "",
        "userReportPath": "",
        "userReportSha256": "",
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
        "audit": run_root / "audit",
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
    task_graph = build_task_graph(requirements)
    write_json(folders["contract"] / "requirements.json", requirements)
    write_json(folders["contract"] / "task-graph.json", task_graph)
    write_json(folders["contract"] / "native-capability-policy.json", capability_policy())
    write_json(folders["contract"] / "language-policy.json", language_policy())
    write_json(folders["contract"] / "tool-policy.json", tool_policy(target))
    write_json(folders["contract"] / "subagent-orchestration-policy.json", orchestration_policy())
    write_json(folders["analysis"] / "analysis-ledger.json", analysis_ledger_template())
    write_json(folders["evidence"] / "research-plan.json", research_plan_template(requirements, target))
    write_json(folders["evidence"] / "source-registry.json", {"schemaVersion": "3.0", "sources": []})
    write_json(folders["design"] / "page-inventory.json", page_inventory_template())
    write_json(folders["design"] / "design-ledger.json", design_ledger_template())
    write_json(folders["implementation"] / "implementation-ledger.json", implementation_ledger_template())
    write_json(folders["audit"] / "copy-audit-ledger.json", copy_audit_template())
    write_json(folders["audit"] / "session-forensics.json", session_forensics_template())
    write_json(folders["review"] / "review.json", review_template())
    write_json(folders["test"] / "test-report.json", test_template())
    write_json(folders["release"] / "release.json", release_template())

    return {
        "requirements": (folders["contract"] / "requirements.json").as_posix(),
        "taskGraph": (folders["contract"] / "task-graph.json").as_posix(),
        "nativeCapabilityPolicy": (folders["contract"] / "native-capability-policy.json").as_posix(),
        "languagePolicy": (folders["contract"] / "language-policy.json").as_posix(),
        "toolPolicy": (folders["contract"] / "tool-policy.json").as_posix(),
        "subagentOrchestrationPolicy": (folders["contract"] / "subagent-orchestration-policy.json").as_posix(),
        "analysisLedger": (folders["analysis"] / "analysis-ledger.json").as_posix(),
        "researchPlan": (folders["evidence"] / "research-plan.json").as_posix(),
        "sourceRegistry": (folders["evidence"] / "source-registry.json").as_posix(),
        "pageInventory": (folders["design"] / "page-inventory.json").as_posix(),
        "designLedger": (folders["design"] / "design-ledger.json").as_posix(),
        "implementationLedger": (folders["implementation"] / "implementation-ledger.json").as_posix(),
        "copyAuditLedger": (folders["audit"] / "copy-audit-ledger.json").as_posix(),
        "sessionForensics": (folders["audit"] / "session-forensics.json").as_posix(),
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
