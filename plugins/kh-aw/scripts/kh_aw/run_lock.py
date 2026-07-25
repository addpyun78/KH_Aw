from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .util import read_json, sha256_file, utc_now, write_json

LOCK_FIELDS = (
    "runId",
    "engineVersion",
    "projectRoot",
    "workspaceRoot",
    "runRoot",
    "analysisMode",
    "analysisFolder",
    "analysisSourceRoot",
    "targetPipeline",
)


def _instruction_sha(state: dict[str, Any]) -> str:
    path = Path(str(state.get("instructionsFile", "")))
    return sha256_file(path) if path.is_file() else ""


def expected_run_lock(state: dict[str, Any]) -> dict[str, Any]:
    payload = {"schemaVersion": "3.0", "lockType": "KH_Aw-run-contract"}
    for field in LOCK_FIELDS:
        payload[field] = state.get(field, "")
    payload["instructionsSha256"] = _instruction_sha(state)
    payload["apkInstallation"] = "forbidden"
    payload["subAgentEveryStage"] = True
    payload["subAgentMinimum"] = 2
    payload["subAgentMaximum"] = 60
    payload["fixedSixtySubAgents"] = False
    payload["promptOnlySubAgentDelegation"] = "forbidden"
    payload["independentSubAgentSessions"] = "required"
    payload["internalLanguage"] = "en"
    payload["userFacingLanguage"] = "ko-KR"
    payload["requiredSlashEvidence"] = "native"
    payload["stageOrder"] = ["intake", "analyze", "research", "design", "implement", "review", "test", "release"]
    return payload


def write_run_lock(run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    payload = expected_run_lock(state)
    payload["generatedAt"] = utc_now()
    path = run_root / "contract" / "run-lock.json"
    write_json(path, payload)
    digest = sha256_file(path)
    checkpoint = run_root / "checkpoints" / "run-lock.last-good.json"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_bytes(path.read_bytes())
    state["runLockPath"] = path.as_posix()
    state["runLockSha256"] = digest
    state["runLockCheckpointSha256"] = sha256_file(checkpoint)
    return {"path": path.as_posix(), "sha256": digest, "checkpoint": checkpoint.as_posix()}


def verify_run_lock(run_root: Path, state: dict[str, Any]) -> list[dict[str, Any]]:
    path = run_root / "contract" / "run-lock.json"
    issues: list[dict[str, Any]] = []
    if not path.is_file():
        return [{"code": "RUN_LOCK_MISSING", "message": 'KH_Aw blocked this operation: run lock missing.'}]
    actual = read_json(path, {})
    expected = expected_run_lock(state)
    for key, value in expected.items():
        if actual.get(key) != value:
            issues.append({"code": "RUN_LOCK_TAMPERED", "message": 'KH_Aw blocked this operation: run lock tampered.', "field": key, "expected": value, "actual": actual.get(key)})
    actual_hash = sha256_file(path)
    if state.get("runLockSha256") != actual_hash:
        issues.append({"code": "RUN_LOCK_HASH_MISMATCH", "message": 'KH_Aw blocked this operation: run lock hash mismatch.', "expected": state.get("runLockSha256"), "actual": actual_hash})
    checkpoint = run_root / "checkpoints" / "run-lock.last-good.json"
    if not checkpoint.is_file() or sha256_file(checkpoint) != state.get("runLockCheckpointSha256"):
        issues.append({"code": "RUN_LOCK_CHECKPOINT_INVALID", "message": 'KH_Aw blocked this operation: run lock checkpoint invalid.'})
    elif checkpoint.read_bytes() != path.read_bytes():
        issues.append({"code": "RUN_LOCK_CHECKPOINT_DIVERGED", "message": 'KH_Aw blocked this operation: run lock checkpoint diverged.'})
    return issues


def restore_run_lock(run_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    checkpoint = run_root / "checkpoints" / "run-lock.last-good.json"
    path = run_root / "contract" / "run-lock.json"
    expected = expected_run_lock(state)
    if checkpoint.is_file():
        checkpoint_payload = read_json(checkpoint, {})
        if all(checkpoint_payload.get(key) == value for key, value in expected.items()):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(checkpoint.read_bytes())
            state["runLockSha256"] = sha256_file(path)
            state["runLockCheckpointSha256"] = sha256_file(checkpoint)
            return {"restored": True, "source": checkpoint.as_posix(), "sha256": state["runLockSha256"]}
    result = write_run_lock(run_root, state)
    return {"restored": True, "source": "regenerated-from-state-and-instructions", **result}
