---
name: kh-aw-full-cycle
description: "Run the complete KH_Aw logic-enforced app/web workflow: immutable intake, exhaustive audit, protected analysis-folder branching, direct web/GitHub body extraction, every-page visual mockups, traced implementation, runtime/tool review, nonterminal auto-repair, and release. Use when prompt-only claims, silent omissions, stage skipping, sample-only mockups, fixed design presets, and APK installation are forbidden."
disable-model-invocation: false
---

# KH_Aw Full Cycle

This skill is an executable workflow, not a prose checklist. Resolve `<plugin-root>` from this skill and run `<plugin-root>/scripts/kh_aw_cli.py`. A stage is complete only when its code gate passes.

## Initialize

1. Save the exact user request without rewriting or shortening it.
2. Run `doctor`.
3. Run `init`; include `--analysis-folder` only when the user actually supplied one.

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py doctor --plugin-root <plugin-root> --marketplace-root <marketplace-root>
python3 <plugin-root>/scripts/kh_aw_cli.py init \
  --project-root <project-root> \
  [--analysis-folder <read-only-analysis-folder>] \
  [--output-root <separate-output-root>] \
  --instructions-file <exact-user-instructions.txt> \
  --target <web-responsive|app-mobile-webview|android-native|ios-native|cross-platform> \
  --name <project-name>
```

Initialization creates `run-lock.json`, an independent lock checkpoint, exact requirement IDs, full inventory, analysis-source protection, native capability policy, target tool policy, and the first physical `/plan` fallback evidence.

## Mandatory order

`intake → analyze → research → design → implement → review → test → release`

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py advance --run-root <run-root> --stage <current-stage> --strict
```

Do not jump stages. The engine returns to the earliest incomplete stage. On failure it writes a repair ticket and `next-action.json`, performs deterministic repair where possible, changes repair strategy after repeated identical failures, reruns physical tools, and rechecks the same gate. Do not stop at `repairing` and do not ask the user to operate the repair loop.

## Mandatory stage-lead and subagent gate

Before producing or passing **every** stage, run the dynamic multi-agent workflow. The engine computes 2-60 independent workers from current project size; fixed 60 and prompt-only delegation are rejected.

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py prepare-agents --run-root <run-root> --stage <stage>
```

Dispatch every planned assignment through Codex `/agents` or an independent Codex task. Save each physical output inside the run root, register it with `record-subagent`, ensure at least one worker cross-reviews another, then register the lead AI aggregation with `aggregate-agents`.

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py agent-status --run-root <run-root> --stage <stage>
```

`agent-status` must pass before `advance`. A native `/agents` fallback inventory is not counted as a completed subagent. Each worker requires a unique independent session ID and unique SHA-256 output.

## Native/slash capability contract

For the current Codex surface, prefer the matching native feature: `/plan`, `/context`, `/agents`, `/artifact`, `/search`, `/diff`, `/review`, `/test`, `/hooks`. When the surface exposes it, save the physical output and register it:

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py record-native \
  --run-root <run-root> --capability-id <id> \
  --evidence-file <physical-output-file> \
  --invocation </slash invocation> --session-id <actual-session-id>
```

A skill-only plugin cannot force the Codex UI to execute a slash command. If native execution is unavailable, run the implemented physical fallback:

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py exercise-native --run-root <run-root> --capability-id <id>
```

The gate requires one verified path. A sentence claiming that a slash function was used is rejected.

## Target toolchain

Before the test gate:

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py bootstrap-tools --run-root <run-root>
python3 <plugin-root>/scripts/kh_aw_cli.py configure-tools --run-root <run-root> [target configuration]
python3 <plugin-root>/scripts/kh_aw_cli.py run-toolchain --run-root <run-root> --strict
```

The runner discovers project features and activates required tools. It captures commands, versions, timestamps, exit codes, logs, artifact paths, and SHA-256. APK installation is forbidden. Do not run `adb install`, `pm install`, `installDebug`, `connectedAndroidTest`, or `bundletool install-apks`.

## Completion

```bash
python3 <plugin-root>/scripts/kh_aw_cli.py finalize --run-root <run-root> --strict
```

Only the engine-created `release/release-receipt.json` permits a completion claim.
