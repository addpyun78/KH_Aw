from __future__ import annotations

import re
from typing import Any

from .util import exact_instruction_lines, utc_now


CLASSIFIERS = [
    ("prohibition", re.compile(r"\b(must not|never|forbid|do not)\b|\uae08\uc9c0|\ud558\uc9c0\s*\ub9c8|\uc548\s*\ub429", re.I)),
    ("evidence", re.compile(r"evidence|proof|log|receipt|\uc99d\uac70|\ub85c\uadf8|\uc601\uc218\uc99d|\uac80\uc99d", re.I)),
    ("installation", re.compile(r"install|cache|shadow|\uc124\uce58|\uce90\uc2dc|\uc12c\ub3c4", re.I)),
    ("research", re.compile(r"research|github|public plugin|\uc870\uc0ac|\uc5f0\uad6c|\uacf5\uac1c", re.I)),
    ("recovery", re.compile(r"resume|checkpoint|repair|\uc7ac\uac1c|\ubcf5\uad6c|\uc218\ub9ac", re.I)),
    ("testing", re.compile(r"test|doctor|e2e|\ud14c\uc2a4\ud2b8|\uc9c4\ub2e8", re.I)),
    ("deliverable", re.compile(r"artifact|output|report|\uc0b0\ucd9c\ubb3c|\ubcf4\uace0\uc11c|\ud30c\uc77c", re.I)),
]


def _classification(line: str) -> list[str]:
    values = [name for name, pattern in CLASSIFIERS if pattern.search(line)]
    return values or ["functional"]


def compile_requirements(instructions: str) -> dict[str, Any]:
    lines = exact_instruction_lines(instructions)
    requirements = []
    coverage = []
    for index, line in enumerate(lines, 1):
        raw_id = f"RAW-{index:04d}"
        req_id = f"REQ-{index:04d}"
        kinds = _classification(line)
        requirements.append({
            "id": req_id,
            "requirement": line,
            "source": raw_id,
            "sourceLine": index,
            "priority": "critical",
            "classifications": kinds,
            "negativeConstraint": "prohibition" in kinds,
            "evidenceRequired": bool({"evidence", "testing", "installation"} & set(kinds)),
            "acceptanceChecks": [],
            "implementationTickets": [],
            "verificationEvidence": [],
            "status": "preserved-unverified",
        })
        coverage.append({
            "id": raw_id,
            "lineNumber": index,
            "sourceText": line,
            "requirementIds": [req_id],
            "status": "preserved-unverified",
            "evidence": [],
        })
    return {
        "schemaVersion": "4.0",
        "generatedAt": utc_now(),
        "compiler": "deterministic-semantic-baseline",
        "aiReviewRequired": True,
        "rawInstructionCount": len(lines),
        "requirements": requirements,
        "rawInstructionCoverage": coverage,
        "omissions": [],
    }
