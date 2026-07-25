# KH_Aw Codex Execution Runbook 3.2

## 1. Preserve the exact instruction

Save the complete user request as UTF-8 without summarizing or rewriting it. The immutable source may contain Korean.

## 2. Validate the package

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py doctor \
  --plugin-root <plugin-root> \
  --marketplace-root <marketplace-root>
```

Do not start a run when doctor fails.

## 3. Initialize the run

When the user supplied an analysis folder, register it as read-only and use a separate output root:

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py init \
  --project-root <result-project> \
  --analysis-folder <read-only-analysis-folder> \
  --output-root <separate-output-root> \
  --instructions-file <exact-user-instructions.txt> \
  --target <target> \
  --name <project-name>
```

Without an analysis folder, omit `--analysis-folder` and work in the actual project. Initialization must create the run lock, requirement ledger, source inventory, language policy, page candidates, orchestration plan, and native capability policy.

## 4. Execute every stage in order

The fixed order is:

```text
intake -> analyze -> research -> design -> implement -> review -> test -> release
```

For every stage:

1. Run `prepare-agents`.
2. Execute every planned assignment in an independent Codex session.
3. Save the physical worker output and rollout JSONL evidence.
4. Run `record-subagent` with worker, task, session, invocation, receipt, output, and session-evidence paths.
5. Ensure at least one worker cross-reviews another worker.
6. Have a separate lead session read all outputs and resolve omissions or conflicts.
7. Run `aggregate-agents` with the lead output and lead session evidence.
8. Run `agent-status`.
9. Run `advance --strict`.

A worker inventory, a fallback claim, or duplicate output is not independent work.

## 5. Use native slash capabilities

Every stage requires native `/goal` and `/agents` evidence. Additional native capabilities are stage-specific. Store the actual invocation, Codex session ID, physical output, and physical Codex rollout JSONL through `record-native`. The rollout must contain both the session identity and slash invocation. A required capability fails closed when the surface cannot provide native evidence; optional capabilities alone may use a physical fallback.

## 6. Research real source bodies

Use `fetch-source` for accessible static sources or `register-source` only with physical native browser extraction evidence. Store the full body, status, length, hash, extraction mode, retrieval time, session, project-fit reason, and affected design or function. Reject search snippets, login walls, access-denied pages, CAPTCHA pages, and empty bodies.

## 7. Design every discovered page

Map every automatic page candidate or exclude it with detailed evidence. Produce a unique visual mockup and comparison board before implementation. Define images, hero or first-viewport signal, typography, color, icons, states, motion, and reduced-motion behavior. Do not use a fixed page-name list or a fixed style preset.

## 8. Implement and verify

Map every design and requirement to physical source files. Run the configured target toolchain:

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py bootstrap-tools --run-root <run-root>
python3 <plugin-root>/scripts/kh_aw_cli.py configure-tools --run-root <run-root> <target-options>
python3 <plugin-root>/scripts/kh_aw_cli.py run-toolchain --run-root <run-root> --strict
```

Web targets require browser and build-output inspection. WebView targets require the Android entry point, bridge, packaged HTML/CSS/JS/images, and APK-content inspection. Native targets require their actual build and runtime evidence. APK installation remains forbidden.

## 9. Enforce the language boundary

Codex-facing prompts, policies, contracts, ledgers, worker assignments, repair tickets, and gate reports are English. Exact user instructions and raw quoted source text may remain in their original language. IDE panel guidance, product fields, buttons, messages, and in-product AI output are Korean. Broken encoding fails.

## 10. Finalize

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py finalize \
  --run-root <run-root> --strict
```

Completion requires all eight current gate reports, exact passed stage states, current hashes, physical target artifacts, a valid Korean user report, zero open repairs, and an engine-created release receipt. `failed`, `blocked`, `not_run`, `repairing`, or `awaiting-receipt` is not completion.
