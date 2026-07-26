from __future__ import annotations

from pathlib import Path
from typing import Any

from .contracts import STAGES, stage_status_passed
from .util import load_state, read_json, sha256_file, utc_now


def verify_run(run_root: Path) -> dict[str, Any]:
    root = run_root.resolve()
    state = load_state(root)
    findings: list[dict[str, Any]] = []
    for stage in STAGES:
        report_path = root / "reports" / f"gate-{stage}.json"
        report = read_json(report_path, {})
        if (
            not stage_status_passed(state.get("stageStatus", {}).get(stage, ""))
            or report.get("pass") is not True
            or report.get("issueCount") != 0
        ):
            findings.append({
                "code": "STAGE_NOT_VERIFIED", "stage": stage,
                "state": state.get("stageStatus", {}).get(stage, ""),
                "gatePath": report_path.as_posix(),
            })
    requirements = read_json(root / "contract" / "requirements.json", {})
    for requirement in requirements.get("requirements", []):
        if not requirement.get("verificationEvidence"):
            findings.append({"code": "REQUIREMENT_EVIDENCE_MISSING", "requirementId": requirement.get("id")})
    receipt_path = root / "release" / "release-receipt.json"
    if not receipt_path.is_file():
        findings.append({"code": "RELEASE_RECEIPT_MISSING"})
    return {
        "schemaVersion": "4.0", "verifiedAt": utc_now(), "runRoot": root.as_posix(),
        "pass": not findings, "findings": findings,
        "releaseReceiptSha256": sha256_file(receipt_path) if receipt_path.is_file() else "",
    }
