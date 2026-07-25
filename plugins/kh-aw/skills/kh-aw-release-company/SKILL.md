---
name: kh-aw-release-company
description: "Review, test, and release app/web products with company-grade physical evidence. Use when Codex must verify every implemented page, run real builds/tests/browsers/emulators/simulators, check accessibility/security/state/performance, preserve rollback/privacy/support/cost details, exclude sensitive artifacts, and prepare GitHub or marketplace releases without false completion claims."
disable-model-invocation: false
---

# KH_Aw Review, Test, and Company Release

## Review

Capture every implemented page from the actual runtime, bind the screenshot to the successful browser/tool execution ID, hash it, and compare it with its approved mockup. Verify regions, fields, logic, features, images, hero, typography, color, icons, motion, reduced motion, states, Korean UI, responsive layout, accessibility, and overlaps. Native `/goal`, `/agents`, `/review`, and `/diff` outputs are required; physical browser and Git evidence is also mandatory and cannot replace them.

## Test tools

Run `bootstrap-tools`, configure only project-specific commands when auto-discovery cannot resolve them, and run `run-toolchain --strict`.

- Web: Chromium, Firefox, WebKit, Playwright, axe, responsive matrix, console/network/broken-image checks, visual regression, Lighthouse.
- Android: Gradle build, unit test, lint, screenshot test, AVD list/boot/health/system screenshot/Logcat. APK installation is prohibited.
- iOS: xcodebuild, unit tests, Simulator list/boot/UI evidence.
- Conditional: TypeScript, npm audit, Firebase Emulator Suite, Docker Compose, Flutter analyze/test/build, AndroidManifest/dependencies, OpenAPI.

Each check must point to a successful execution, log, SHA-256, and physical output. Free-form `pass: true` text fails.

## Release

Run security scanning. Record artifact hashes, installation instructions, rollback, privacy, support, cost ledger, and release notes. Exclude secrets, browser profiles, cookie/login databases, runtime data, caches, logs, backups, and dependency folders. Run release gate and `finalize --strict`. GitHub push and public OpenAI directory approval are separate and may be claimed only after they physically occur.

## Mandatory multi-agent execution

This skill participates in the KH_Aw stage gate. Before the stage can pass, run `prepare-agents`, execute every planned assignment as an independent Codex subagent (`/agents`) or independent Codex task, register physical outputs with `record-subagent`, perform cross-review, and register the stage lead aggregation with `aggregate-agents`. The canonical count is dynamically calculated from 2 to 60 and cannot be weakened by editing JSON or by a prose claim.
