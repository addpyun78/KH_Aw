---
name: kh-aw-audit-upgrade
description: "Perform a no-omission KH_Aw audit and logic upgrade of an existing app/web repository or a separately supplied read-only analysis folder. Use when Codex must inventory every file, preserve every instruction line, identify architecture/logic/security/design defects, protect source inputs, and produce evidence-backed upgrade targets before editing."
disable-model-invocation: false
---

# KH_Aw Audit and Upgrade

Run the KH_Aw CLI. Do not substitute a written audit for the machine inventory and analysis gate.

- Analysis folder supplied: source is read-only, archived, hashed, mutation-checked, and auto-restored. Product/output/workspace stay outside it.
- No analysis folder: inspect the current project and keep evidence under its separate `.kh_aw` workspace.

The analyze gate requires one physical inventory row per file, SHA-256, complete project structure, architecture, every page/region/field/logic/feature, file-level findings, security, performance, design, strengths, weaknesses, risks, and upgrade targets. `run-lock.json` prevents the mode or paths from being silently changed.

Use `/goal`, `/context`, `/agents`, and `/artifact`, then register their actual outputs and Codex rollout JSONL evidence. Missing native slash evidence blocks the stage. Run `advance --stage analyze --strict`; repair the actual source/evidence and rerun until passed.

## Mandatory multi-agent execution

This skill participates in the KH_Aw stage gate. Before the stage can pass, run `prepare-agents`, execute every planned assignment as an independent Codex subagent (`/agents`) or independent Codex task, register physical outputs with `record-subagent`, perform cross-review, and register the stage lead aggregation with `aggregate-agents`. The canonical count is dynamically calculated from 2 to 60 and cannot be weakened by editing JSON or by a prose claim.
