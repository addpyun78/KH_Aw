from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .util import sha256_file, utc_now


CLAIM_PATTERN = re.compile(r"(?<=[.!?\u3002])\s+|\n+")


def verify_claims(text: str, evidence_paths: list[Path], root: Path | None = None) -> dict[str, Any]:
    evidence = []
    for path in evidence_paths:
        candidate = path if path.is_absolute() or root is None else root / path
        if candidate.is_file():
            evidence.append({
                "path": candidate.as_posix(),
                "sha256": sha256_file(candidate),
                "bytes": candidate.stat().st_size,
            })
    claims = [item.strip() for item in CLAIM_PATTERN.split(text) if item.strip()]
    bindings = [{
        "claimId": f"CLAIM-{index:04d}",
        "text": claim,
        "evidence": evidence,
        "status": "evidence-linked" if evidence else "unverified",
    } for index, claim in enumerate(claims, 1)]
    return {
        "schemaVersion": "4.0", "generatedAt": utc_now(),
        "claims": bindings,
        "verified": bool(bindings) and all(item["status"] == "evidence-linked" for item in bindings),
    }
