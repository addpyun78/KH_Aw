from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .util import read_json, sha256_file, utc_now, write_json

SLASH_RE = re.compile(r"(?<!\w)/(?:goal|plan|context|agents|search|artifact|diff|review|test|hooks)\b")


def _strings(value: Any):
    if isinstance(value, dict):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)
    elif isinstance(value, str):
        yield value


def build_session_forensics(run_root: Path, session_jsonl: Path, session_id: str) -> dict[str, Any]:
    source = session_jsonl.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(source)
    if len(session_id.strip()) < 8:
        raise ValueError("session_id must identify the physical Codex session")

    event_count = 0
    parse_errors = 0
    slash_invocations: list[str] = []
    final_claims: list[str] = []
    source_mentions_session = session_id in source.name
    with source.open("r", encoding="utf-8", errors="strict") as stream:
        for line in stream:
            if not line.strip():
                continue
            event_count += 1
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                parse_errors += 1
                continue
            joined = "\n".join(_strings(event))
            source_mentions_session = source_mentions_session or session_id in joined
            slash_invocations.extend(SLASH_RE.findall(joined))
            if '"final"' in line or '"final_answer"' in line:
                final_claims.append(joined[:4000])

    test_report = read_json(run_root / "test" / "test-report.json", {})
    commands = [
        {
            "executionId": item.get("executionId"),
            "toolId": item.get("toolId"),
            "command": item.get("command"),
            "exitCode": item.get("exitCode"),
            "status": item.get("status"),
        }
        for item in test_report.get("toolExecutions", [])
        if isinstance(item, dict)
    ]
    failed_commands = [item for item in commands if item.get("exitCode") != 0 or item.get("status") != "passed"]

    capability_policy = read_json(run_root / "contract" / "native-capability-policy.json", {})
    required_ids = {
        str(item.get("id"))
        for item in capability_policy.get("capabilities", [])
        if isinstance(item, dict) and item.get("required") is True
    }
    records = {
        str(item.get("capabilityId")): item
        for item in capability_policy.get("records", [])
        if isinstance(item, dict)
    }
    capability_findings = []
    evidence_mismatches = []
    for capability_id in sorted(required_ids):
        record = records.get(capability_id)
        valid = bool(
            record
            and record.get("mode") == "native"
            and record.get("status") == "verified"
            and record.get("sessionId") == session_id
            and str(record.get("preferredSlash", "")) in slash_invocations
        )
        capability_findings.append({
            "capabilityId": capability_id,
            "preferredSlash": record.get("preferredSlash") if record else "",
            "recordedSessionId": record.get("sessionId") if record else "",
            "foundInSession": valid,
        })
        if not valid:
            evidence_mismatches.append({
                "type": "native-capability-session-mismatch",
                "capabilityId": capability_id,
            })

    not_run = []
    if event_count == 0 or parse_errors:
        not_run.append("valid-session-event-stream")
    if not source_mentions_session:
        not_run.append("session-id-binding")

    payload = {
        "schemaVersion": "3.2",
        "generatedAt": utc_now(),
        "sessionId": session_id,
        "sourceSessionPath": source.as_posix(),
        "sourceSessionSha256": sha256_file(source),
        "sourceSessionEventCount": event_count,
        "sourceSessionParseErrors": parse_errors,
        "commands": commands,
        "failedCommands": failed_commands,
        "notRunRequiredChecks": not_run,
        "finalReportClaims": final_claims,
        "evidenceMismatches": evidence_mismatches,
        "slashCapabilityFindings": capability_findings,
        "completionTruth": "verified" if not failed_commands and not not_run and not evidence_mismatches else "blocked",
        "omissions": [],
    }
    write_json(run_root / "audit" / "session-forensics.json", payload)
    return payload

