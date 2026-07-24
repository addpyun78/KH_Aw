from __future__ import annotations

from pathlib import Path
from typing import Any

from .util import read_json, sha256_file, utc_now, write_json

# Codex UI slash/native features cannot be invoked by a skill-only plugin as a subprocess.
# KH_Aw therefore treats each feature as a capability contract: prefer native evidence when
# the surface exposes it, otherwise execute a deterministic physical fallback and record it.
NATIVE_CAPABILITIES: list[dict[str, Any]] = [
    {"id": "codex-plan", "stage": "intake", "preferredSlash": "/plan", "fallback": "kh-aw-state-plan", "required": True},
    {"id": "codex-agents-intake", "stage": "intake", "preferredSlash": "/agents", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-context", "stage": "analyze", "preferredSlash": "/context", "fallback": "kh-aw-context-inventory", "required": True},
    {"id": "codex-agents-analyze", "stage": "analyze", "preferredSlash": "/agents", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-artifact-analysis", "stage": "analyze", "preferredSlash": "/artifact", "fallback": "kh-aw-analysis-artifacts", "required": True},
    {"id": "codex-agents-research", "stage": "research", "preferredSlash": "/agents", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-web-research", "stage": "research", "preferredSlash": "/search", "fallback": "kh-aw-body-fetch-registry", "required": True},
    {"id": "codex-agents-design", "stage": "design", "preferredSlash": "/agents", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-artifact-design", "stage": "design", "preferredSlash": "/artifact", "fallback": "kh-aw-mockup-artifacts", "required": True},
    {"id": "codex-agents-implement", "stage": "implement", "preferredSlash": "/agents", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-diff-implement", "stage": "implement", "preferredSlash": "/diff", "fallback": "git-diff-physical", "required": True},
    {"id": "codex-agents-review", "stage": "review", "preferredSlash": "/agents", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-review", "stage": "review", "preferredSlash": "/review", "fallback": "kh-aw-browser-review", "required": True},
    {"id": "codex-diff-review", "stage": "review", "preferredSlash": "/diff", "fallback": "git-diff-physical", "required": True},
    {"id": "codex-agents-test", "stage": "test", "preferredSlash": "/agents", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-test", "stage": "test", "preferredSlash": "/test", "fallback": "kh-aw-toolchain", "required": True},
    {"id": "codex-hooks", "stage": "test", "preferredSlash": "/hooks", "fallback": "kh-aw-gate-event-log", "required": True},
    {"id": "codex-agents-release", "stage": "release", "preferredSlash": "/agents", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-artifact-release", "stage": "release", "preferredSlash": "/artifact", "fallback": "kh-aw-release-artifacts", "required": True},
    {"id": "codex-diff-release", "stage": "release", "preferredSlash": "/diff", "fallback": "git-diff-physical", "required": True},
]


def capability_policy() -> dict[str, Any]:
    return {
        "schemaVersion": "3.0",
        "generatedAt": utc_now(),
        "rule": "가능한 Codex 네이티브/슬러시 기능을 우선 사용한다. 현재 표면에서 사용할 수 없으면 물리 명령·파일·해시 기반 fallback을 실제 실행한다. 문장 주장만으로 통과하지 않는다.",
        "capabilities": [dict(item) for item in NATIVE_CAPABILITIES],
        "records": [],
    }


def _relative(run_root: Path, path: Path) -> str:
    return path.resolve().relative_to(run_root.resolve()).as_posix()


def record_capability(
    run_root: Path,
    *,
    capability_id: str,
    mode: str,
    evidence_file: Path,
    invocation: str,
    tool_execution_ids: list[str] | None = None,
    session_id: str = "",
) -> dict[str, Any]:
    policy_path = run_root / "contract" / "native-capability-policy.json"
    policy = read_json(policy_path, {})
    definitions = {item.get("id"): item for item in policy.get("capabilities", []) if isinstance(item, dict)}
    if capability_id not in definitions:
        raise ValueError(f"unknown capability: {capability_id}")
    if mode not in {"native", "fallback"}:
        raise ValueError("mode must be native or fallback")
    definition = definitions[capability_id]
    if mode == "native":
        preferred = str(definition.get("preferredSlash", ""))
        if not session_id.strip():
            raise ValueError("native capability evidence requires a Codex session ID")
        if preferred and preferred not in invocation:
            raise ValueError(f"native invocation must contain {preferred}")
    evidence_file = evidence_file.resolve()
    if not evidence_file.is_file() or evidence_file.stat().st_size < 16:
        raise ValueError("capability evidence file must exist and contain physical output")
    try:
        rel = _relative(run_root, evidence_file)
    except ValueError as exc:
        raise ValueError("capability evidence must stay inside run root") from exc
    record = {
        "id": f"CAP-{len(policy.setdefault('records', [])) + 1:04d}",
        "capabilityId": capability_id,
        "stage": definitions[capability_id].get("stage"),
        "mode": mode,
        "preferredSlash": definitions[capability_id].get("preferredSlash"),
        "invocation": invocation.strip(),
        "evidencePath": rel,
        "evidenceSha256": sha256_file(evidence_file),
        "evidenceBytes": evidence_file.stat().st_size,
        "toolExecutionIds": list(tool_execution_ids or []),
        "sessionId": session_id,
        "verifiedAt": utc_now(),
        "status": "verified",
    }
    policy["records"] = [item for item in policy.get("records", []) if item.get("capabilityId") != capability_id]
    policy["records"].append(record)
    write_json(policy_path, policy)
    return record


def canonical_capability_ids() -> list[str]:
    return [str(item["id"]) for item in NATIVE_CAPABILITIES if item.get("required") is True]


def capability_records_for_stage(run_root: Path, stage: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    policy = read_json(run_root / "contract" / "native-capability-policy.json", {})
    required = [dict(item) for item in NATIVE_CAPABILITIES if item.get("stage") == stage and item.get("required") is True]
    records = [item for item in policy.get("records", []) if isinstance(item, dict) and item.get("stage") == stage]
    return required, records
