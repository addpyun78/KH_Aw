---
name: kh-aw-implementation-repair
description: "Implement approved KH_Aw every-page mockups and continuously repair failed evidence gates without terminal stopping. Use when Codex must bind real images, implement purposeful motion and reduced-motion, trace regions/fields/logic/features, hash target files, diagnose root causes, change repair strategy after repeated failure, and resume automatically."
disable-model-invocation: false
---

# KH_Aw Implementation and Nonterminal Repair

Implementation starts only after the design gate passes. Every page ledger entry must point to real project files and current hashes. Region, field, logic, feature, image, and motion IDs must occur in executable/markup context rather than comments. Each traced ID must also be covered by a real test file with current hash.

Images require physical files, SHA-256, provenance or generation prompt, rights/ownership, project-fit reason, and code usage locations. Motion requires physical implementation markers, purpose, timing/easing, and reduced-motion code.

Use `/goal`, `/agents`, and `/diff`, then register their outputs and Codex rollout JSONL evidence. Physical Git or SHA-256 comparison is additional implementation evidence and cannot replace `/diff`. On gate failure, the engine restores protected inputs, regenerates damaged contracts, removes forbidden design-selection keys, executes mapped repair actions, creates a root-cause ticket, and reruns. Do not close or skip the ticket manually; the gate report hash closes it automatically after success.

## Mandatory multi-agent execution

This skill participates in the KH_Aw stage gate. Before the stage can pass, run `prepare-agents`, execute every planned assignment as an independent Codex subagent (`/agents`) or independent Codex task, register physical outputs with `record-subagent`, perform cross-review, and register the stage lead aggregation with `aggregate-agents`. The canonical count is dynamically calculated from 2 to 60 and cannot be weakened by editing JSON or by a prose claim.
