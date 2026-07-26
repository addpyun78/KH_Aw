---
name: kh-aw-multi-agent-orchestration
description: "Execute KH_Aw's logic-enforced stage-lead and independent subagent system for every intake, analysis, research, design, implementation, review, test, and release stage. The engine computes a safety floor and requires 2-60 real independent Codex subagents, immutable dispatch contracts, physical invocation receipts, unique outputs, full ring cross-review, and lead aggregation. Prompt-only delegation, under-allocation, copied outputs, and fixed 60-agent fan-out are rejected."
disable-model-invocation: false
---

# KH_Aw Multi-Agent Orchestration 3.2

This skill is mandatory for **every KH_Aw stage**. It is not a prose recommendation. The Python gate recomputes project complexity and reads physical orchestration files. A sentence claiming that subagents were used never passes.

## 1. Compute and lock the stage safety floor

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py prepare-agents \
  --run-root <run-root> --stage <stage>
```

The engine calculates the minimum safe worker count from physical project signals such as file count, directory count, requirements, pages, fields, logic, features, risks, research elements, required tools, and release artifacts.

- Every stage must use at least 2 independent subagents.
- No stage may use more than 60.
- Small projects start near 2.
- Large projects scale upward.
- A lead may never reduce the count below the calculated safety floor.
- A lead may increase the count, up to 60, only with a project-specific physical justification file of at least 120 bytes.
- Selecting 60 for a low/medium-complexity project is rejected.

Lead-controlled increase example:

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py prepare-agents \
  --run-root <run-root> \
  --stage <stage> \
  --count <2-60> \
  --justification-file <run-root>/orchestration/<stage>/lead-scale-reason.md \
  --force
```

The engine creates:

```text
orchestration/<stage>/agent-plan.json
orchestration/<stage>/dispatch-manifest.json
orchestration/<stage>/dispatch/<worker-id>.json
orchestration/<stage>/lead-contract.json
```

Do not edit these files manually. Their physical SHA-256 values are checked by the stage gate.

## 2. Dispatch real independent Codex subagents

For every assignment, invoke a real independent Codex subagent through the active subagent tool or an independent Codex task. Repeated self-review, a generated assignment list, or prose claiming delegation does not replace a physical independent session.

Each worker receives its own immutable dispatch JSON. The worker must use:

- planned worker ID;
- planned task ID;
- unique role shard;
- assigned scope IDs;
- dispatch-contract SHA-256;
- planned ring-review target;
- a unique Codex session ID.

Each worker writes a different physical result file under:

```text
<run-root>/orchestration/<stage>/outputs/<worker-id>.*
```

## 3. Write the physical invocation receipt

Every actual subagent invocation must have a separate JSON receipt inside the run root:

```json
{
  "schemaVersion": "3.2",
  "stage": "analyze",
  "workerId": "ANALYZE-AGENT-01",
  "taskId": "ANALYZE-TASK-01",
  "sessionId": "actual-independent-session-id",
  "delegationMode": "native-agents",
  "invocation": "active Codex subagent tool ...",
  "dispatchContractSha256": "<64 lowercase hex>",
  "issuedAt": "<ISO-8601 timestamp>"
}
```

The receipt must match the immutable assignment exactly. A missing, copied, modified, or run-root-external receipt is rejected.

## 4. Full ring cross-review

Every worker reviews one different worker according to `reviewTargetWorkerIds`. The plan forms a ring, so every result is reviewed at least once. It is not sufficient to appoint only one final reviewer.

The physical worker output must contain:

- worker ID;
- task ID;
- session ID;
- dispatch-contract SHA-256;
- at least one assigned scope ID;
- every planned reviewed worker ID;
- the worker's substantive findings and result.

## 5. Register each completed worker

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py record-subagent \
  --run-root <run-root> \
  --stage <stage> \
  --worker-id <planned-worker-id> \
  --task-id <planned-task-id> \
  --session-id <actual-independent-codex-session-id> \
  --invocation "<actual Codex subagent invocation>" \
  --delegation-mode native-agents \
  --invocation-receipt-file <physical-invocation-receipt.json> \
  --evidence-file <physical-worker-output> \
  --review-of <planned-review-target-worker-id>
```

For an independent Codex task, use:

```bash
--delegation-mode native-agents
```

The engine rejects reused sessions, reused receipts, reused output hashes, missing identity markers, dispatch tampering, role/task mismatch, files outside the run root, incomplete ring review, and fake fallback records.

## 6. Lead AI aggregation

The stage lead AI uses a session distinct from every worker. It must read every registered result, remove duplicates, resolve conflicts, find uncovered scope, update the real project/stage artifacts, and write a physical aggregation file containing:

- lead agent ID;
- lead session ID;
- plan fingerprint;
- lead-contract SHA-256;
- every accepted worker ID;
- coverage/conflict decisions.

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py aggregate-agents \
  --run-root <run-root> \
  --stage <stage> \
  --lead-agent-id <stage-lead-id> \
  --lead-session-id <lead-session-id-distinct-from-workers> \
  --evidence-file <run-root>/orchestration/<stage>/lead-aggregation.md \
  [--resolved-conflict <description>]
```

## 7. Verify before advancing

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py agent-status \
  --run-root <run-root> --stage <stage>
```

Only after `agent-status` succeeds may the lead run:

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py advance \
  --run-root <run-root> --stage <stage> --strict
```

A missing worker, count below the safety floor, unjustified increase, fixed 60, invalid session, duplicate output, duplicate receipt, broken dispatch contract, incomplete ring review, or incomplete lead aggregation creates a nonterminal repair action. Preserve valid outputs, repair only the missing/invalid parts, and rerun the same stage.
