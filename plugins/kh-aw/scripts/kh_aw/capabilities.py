from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .util import read_json, sha256_file, utc_now, write_json

# Capabilities describe behavior. A slash command is only preferred when the active
# Codex surface actually exposes it; physical tool/subagent evidence is also valid.
NATIVE_CAPABILITIES: list[dict[str, Any]] = [
    {"id": "codex-goal-intake", "stage": "intake", "preferredSlash": "/goal", "fallback": "kh-aw-stage-goal", "required": True},
    {"id": "codex-plan", "stage": "intake", "preferredSlash": "/plan", "fallback": "kh-aw-state-plan", "required": True},
    {"id": "codex-agents-intake", "stage": "intake", "preferredSlash": "", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-goal-analyze", "stage": "analyze", "preferredSlash": "/goal", "fallback": "kh-aw-stage-goal", "required": True},
    {"id": "codex-context", "stage": "analyze", "preferredSlash": "", "fallback": "kh-aw-context-inventory", "required": True},
    {"id": "codex-agents-analyze", "stage": "analyze", "preferredSlash": "", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-artifact-analysis", "stage": "analyze", "preferredSlash": "", "fallback": "kh-aw-analysis-artifacts", "required": True},
    {"id": "codex-goal-research", "stage": "research", "preferredSlash": "/goal", "fallback": "kh-aw-stage-goal", "required": True},
    {"id": "codex-agents-research", "stage": "research", "preferredSlash": "", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-web-research", "stage": "research", "preferredSlash": "", "fallback": "kh-aw-body-fetch-registry", "required": True},
    {"id": "codex-artifact-research", "stage": "research", "preferredSlash": "", "fallback": "kh-aw-research-artifacts", "required": True},
    {"id": "codex-goal-design", "stage": "design", "preferredSlash": "/goal", "fallback": "kh-aw-stage-goal", "required": True},
    {"id": "codex-plan-design", "stage": "design", "preferredSlash": "/plan", "fallback": "kh-aw-design-plan", "required": True},
    {"id": "codex-agents-design", "stage": "design", "preferredSlash": "", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-artifact-design", "stage": "design", "preferredSlash": "", "fallback": "kh-aw-mockup-artifacts", "required": True},
    {"id": "codex-goal-implement", "stage": "implement", "preferredSlash": "/goal", "fallback": "kh-aw-stage-goal", "required": True},
    {"id": "codex-agents-implement", "stage": "implement", "preferredSlash": "", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-diff-implement", "stage": "implement", "preferredSlash": "", "fallback": "git-diff-physical", "required": True},
    {"id": "codex-goal-review", "stage": "review", "preferredSlash": "/goal", "fallback": "kh-aw-stage-goal", "required": True},
    {"id": "codex-agents-review", "stage": "review", "preferredSlash": "", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-review", "stage": "review", "preferredSlash": "/review", "fallback": "kh-aw-browser-review", "required": True},
    {"id": "codex-diff-review", "stage": "review", "preferredSlash": "", "fallback": "git-diff-physical", "required": True},
    {"id": "codex-goal-test", "stage": "test", "preferredSlash": "/goal", "fallback": "kh-aw-stage-goal", "required": True},
    {"id": "codex-agents-test", "stage": "test", "preferredSlash": "", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-test", "stage": "test", "preferredSlash": "", "fallback": "kh-aw-toolchain", "required": True},
    {"id": "codex-hooks", "stage": "test", "preferredSlash": "/hooks", "fallback": "kh-aw-gate-event-log", "required": False},
    {"id": "codex-goal-release", "stage": "release", "preferredSlash": "/goal", "fallback": "kh-aw-stage-goal", "required": True},
    {"id": "codex-agents-release", "stage": "release", "preferredSlash": "", "fallback": "kh-aw-agent-dispatch-manifest", "required": True},
    {"id": "codex-artifact-release", "stage": "release", "preferredSlash": "", "fallback": "kh-aw-release-artifacts", "required": True},
    {"id": "codex-diff-release", "stage": "release", "preferredSlash": "", "fallback": "git-diff-physical", "required": True},
]


def capability_policy() -> dict[str, Any]:
    return {
        "schemaVersion": "4.0",
        "generatedAt": utc_now(),
        "requiredEvidenceMode": "physical-capability",
        "fallbackSatisfiesRequiredCapability": True,
        "rule": "Verify required behavior with native Codex evidence when available, otherwise with a physical tool or subagent receipt. Unsupported slash names are never mandatory.",
        "capabilities": [dict(item) for item in NATIVE_CAPABILITIES],
        "records": [],
    }


def _relative(run_root: Path, path: Path) -> str:
    return path.resolve().relative_to(run_root.resolve()).as_posix()


def _validate_native_session_evidence(
    path: Path,
    *,
    session_id: str,
    preferred_slash: str,
) -> tuple[str, str, int]:
    path = path.expanduser().resolve()
    normalized = path.as_posix().lower()
    if "/.codex/sessions/" not in normalized or not path.name.lower().startswith("rollout-") or path.suffix.lower() != ".jsonl":
        raise ValueError("native slash session evidence must be a physical Codex rollout JSONL under .codex/sessions")
    if not path.is_file() or path.stat().st_size < 128:
        raise ValueError("native slash Codex session JSONL is missing or too small")
    event_count = 0
    session_found = session_id in path.name
    slash_found = False
    with path.open("r", encoding="utf-8", errors="strict") as stream:
        for line in stream:
            if not line.strip():
                continue
            event_count += 1
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError("native slash Codex session JSONL contains invalid events") from exc
            serialized = json.dumps(event, ensure_ascii=False)
            session_found = session_found or session_id in serialized
            slash_found = slash_found or preferred_slash in serialized
    if not session_found or not slash_found:
        raise ValueError("native slash Codex session JSONL is not bound to the session and slash invocation")
    return path.as_posix(), sha256_file(path), event_count


def record_capability(
    run_root: Path,
    *,
    capability_id: str,
    mode: str,
    evidence_file: Path,
    invocation: str,
    tool_execution_ids: list[str] | None = None,
    session_id: str = "",
    session_evidence_file: Path | None = None,
) -> dict[str, Any]:
    policy_path = run_root / "contract" / "native-capability-policy.json"
    policy = read_json(policy_path, {})
    definitions = {item.get("id"): item for item in policy.get("capabilities", []) if isinstance(item, dict)}
    if capability_id not in definitions:
        raise ValueError(f"unknown capability: {capability_id}")
    if mode not in {"native", "fallback"}:
        raise ValueError("mode must be native or fallback")
    definition = definitions[capability_id]
    session_evidence_path = ""
    session_evidence_sha256 = ""
    session_evidence_event_count = 0
    if mode == "native":
        preferred = str(definition.get("preferredSlash", ""))
        if not session_id.strip():
            raise ValueError("native capability evidence requires a Codex session ID")
        if len(session_id.strip()) < 8:
            raise ValueError("native capability evidence requires a stable Codex session ID")
        if preferred and preferred not in invocation:
            raise ValueError(f"native invocation must contain {preferred}")
        if session_evidence_file is None:
            raise ValueError("native capability evidence requires a physical Codex session JSONL")
        session_evidence_path, session_evidence_sha256, session_evidence_event_count = _validate_native_session_evidence(
            session_evidence_file,
            session_id=session_id.strip(),
            preferred_slash=preferred,
        )
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
        "sessionEvidencePath": session_evidence_path,
        "sessionEvidenceSha256": session_evidence_sha256,
        "sessionEvidenceEventCount": session_evidence_event_count,
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
