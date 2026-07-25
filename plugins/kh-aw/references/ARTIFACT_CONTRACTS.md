# KH_Aw Artifact Contracts

All paths are relative to the `workspaceRoot` stored in `kh-aw-state.json`.

## contract/instruction-ledger.json

Each non-empty source line keeps its exact text, line number, derived requirement IDs, coverage state, evidence, verification method, and omission owner. Original user text may remain Korean because it is immutable source evidence.

## contract/requirements.json

Every requirement has an ID, exact source, plain explanation, target relevance, priority, acceptance checks, status, stage coverage, evidence files, verification method, and omission classification. `partial`, `missing`, or `blocked` cannot pass release.

## contract/source-inventory.json

Stores every source file path, kind, size, SHA-256, and audit classification. When an analysis folder was supplied, its before and after hashes must match.

## analysis/analysis-ledger.json

Required collections include requirement coverage, page candidates, fields, logic, features, risks, omissions, source-folder evidence, and one exhaustive file finding for every inventoried source path.

## evidence/research-plan.json and evidence/source-registry.json

Every research element identifies required source classes and project-fit reasons. An accepted source requires a real URL, successful retrieval, a non-empty extracted body, body length, SHA-256, excerpt, retrieval timestamp, extraction mode, native browser session evidence, freshness, and links to the page, feature, or design decision it affects. Search snippets are not source bodies.

## design/page-inventory.json

Every automatically discovered candidate must be mapped to a page or explicitly excluded with evidence and a detailed reason. Each required page records its route or entry point, regions, fields, actions, states, origin, and reason. Fixed universal page names are forbidden.

## design/design-ledger.json

Every page has an independent visual mockup, design rationale, image plan, icon plan, typography plan, color plan, hero or first-viewport strategy, motion storyboard, reduced-motion behavior, required states, and source evidence. The comparison board must include every page.

## implementation/implementation-ledger.json

Each page, field, logic item, researched feature, image, hero, icon, motion, and state maps to physical source paths and verification evidence. A declaration without files does not count.

## review/review.json

Every page stores a real screenshot and an independent semantic review of structure, fields, logic, features, images, hero, typography, color, icons, motion, reduced motion, Korean UI text, states, responsive behavior, accessibility, and overlap. Automated browser output cannot approve semantic quality by itself.

## test/test-report.json

Every required command stores command text, version, exit code, log path, log SHA-256, artifact paths, and artifact hashes. It also records browser engines, accessibility, Lighthouse, visual regression, Android or iOS runtime evidence, and APK or web build-content inspection.

## audit/copy-audit-ledger.json

Every result file that matches an analysis-source hash is classified. Unexplained files, bulk copies, and copied legacy UI implementations fail. Reference-only material belongs under `.kh_aw/reference`.

## audit/session-forensics.json

Stores the physical Codex rollout JSONL path and hash, parsed event count, slash invocations, commands, command failures, mismatches, and completion truth. Self-authored summaries are not accepted.

## repairs/REPAIR-*.json

A repair ticket records the owning stage, exact issue codes, strategy, physical actions, rerun evidence, and closure evidence. Editing the report to say `passed` is not repair.

## release/release-receipt.json

Only the engine creates the receipt after all eight current gate reports pass with matching hashes, no open repairs, exact passed stage states, a valid user-facing Korean report, and verified build evidence. A pre-created receipt or stale receipt is invalid.
