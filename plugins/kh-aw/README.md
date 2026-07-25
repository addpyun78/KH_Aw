# KH_Aw Codex Plugin 3.2.0

- Display name: **KH_Aw**
- Plugin ID: **kh-aw**
- Target: Codex Git marketplace and plugin installation
- Independent workers per stage: **dynamic minimum 2, maximum 60**
- APK installation: **forbidden**

## Included skills

1. `kh-aw-full-cycle`: all eight stages and repair flow
2. `kh-aw-multi-agent-orchestration`: stage lead plus 2-60 independent workers
3. `kh-aw-audit-upgrade`: exhaustive file, requirement, and logic audit
4. `kh-aw-research-design`: direct source-body extraction and every-page mockups
5. `kh-aw-implementation-repair`: physical implementation evidence and repair
6. `kh-aw-release-company`: target tool verification and release controls

## Command entry points

```bash
python3 scripts/kh_aw_cli.py doctor --plugin-root . --marketplace-root ../..
python3 scripts/kh_aw_cli.py init --project-root <project> --instructions-file <exact.txt> --target <target>
python3 scripts/kh_aw_cli.py prepare-agents --run-root <run> --stage <stage>
python3 scripts/kh_aw_cli.py record-subagent ...
python3 scripts/kh_aw_cli.py aggregate-agents ...
python3 scripts/kh_aw_cli.py agent-status --run-root <run> --stage <stage>
python3 scripts/kh_aw_cli.py advance --run-root <run> --stage <stage> --strict
python3 scripts/kh_aw_cli.py run-toolchain --run-root <run> --strict
python3 scripts/kh_aw_cli.py finalize --run-root <run> --strict
```

## Physical worker gate

Every stage recalculates a project-specific 2-60 worker plan. The gate compares the saved count, roles, assignments, and fingerprint with the calculated plan, so lowering the plan manually cannot pass.

Every worker requires:

- a planned worker, task, and role;
- an independent Codex session ID;
- a physical Codex rollout JSONL file;
- a native `/agents` invocation or a genuinely independent Codex task;
- a physical output inside the run root;
- a unique SHA-256;
- at least one cross-review across the worker set; and
- a lead aggregation that accepts every required worker.

An `exercise-native` fallback inventory is not worker-completion evidence.

## Tool verification

Web targets require configured browser engines, accessibility, Lighthouse, and visual checks. Android targets require Gradle, screenshot tests, AVD or ADB state, and Logcat evidence. iOS targets require `xcodebuild` and Simulator evidence. A required tool does not pass without a physical log, exit code, version, artifact, and SHA-256.

Android APK installation commands are rejected before execution and detected again in recorded command evidence.

## Language boundary

Codex-facing prompts, policies, contracts, ledgers, gate messages, repair tickets, and worker instructions are English. User-visible IDE panel guidance and the generated app or web interface remain Korean. A release fails when internal evidence contains Korean or broken encoding, or when a Korean-targeted product has no Korean interface text.
