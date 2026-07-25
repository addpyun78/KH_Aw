# KH_Aw Executable Enforcement Contract

## 1. Purpose

KH_Aw is a Codex plugin that audits a real app or web project, extracts direct web and GitHub bodies, designs every discovered page before implementation, implements physical code and assets, verifies actual runtime artifacts, and repairs failures without silently converting them into completion.

This contract is not a prompt checklist. `scripts/kh_aw_cli.py` and its imported gate modules decide stage truth from physical files, current hashes, exhaustive inventories, real tool results, screenshots, and independent Codex session evidence.

## 2. Target and source separation

### 2.1 User-supplied analysis folder

1. Lock `analysisMode` as `provided`.
2. Treat the analysis folder as read-only source evidence.
3. Record a complete file inventory and SHA-256 snapshot before work.
4. Create implementation output outside the analysis folder.
5. Recompute the source inventory at later gates and fail on mutation.
6. Keep optional reference copies only under `.kh_aw/reference`.
7. Link every analysis conclusion to file-level evidence.

### 2.2 No analysis folder

1. Lock `analysisMode` as `not-provided`.
2. Use the current project as the implementation target.
3. Keep `.kh_aw` as evidence and state only.
4. Exclude `.kh_aw`, `.git`, dependencies, and build caches from source analysis.
5. Permit implementation changes only inside the target project.

### 2.3 Target pipeline

Classify and lock one target: `web-responsive`, `app-mobile-webview`, `android-native`, `ios-native`, or `cross-platform`. Ambiguous targets must be confirmed. Target-specific gates cannot be substituted by another pipeline.

## 3. Fixed stage machine

The only stage order is:

1. `intake`: preserve exact instructions, derive traceable requirements, lock target and policies.
2. `analyze`: exhaustively inventory files, pages, fields, logic, features, and risks.
3. `research`: extract real source bodies and map findings to project decisions.
4. `design`: create project-specific every-page mockups and implementation contracts.
5. `implement`: create physical code, assets, states, bridges, and data paths.
6. `review`: compare every actual page with its mockup and semantic requirements.
7. `test`: run target build, runtime, browser, accessibility, performance, and artifact checks.
8. `release`: verify security, source immutability, all current gate hashes, and user reporting.

Only exact allowed stage statuses pass. Prefixes such as `passed-fake` do not pass. A failed stage becomes `repairing`, `blocked`, `failed`, or `not_run`; none is completion.

## 4. Run lock and immutable policy

Initialization creates `run-lock.json` and a matching checkpoint. Every gate verifies their current content and hashes. The lock includes:

- target pipeline;
- project, analysis, implementation, output, and run roots;
- exact instruction hash;
- required internal language `en`;
- required user-facing language `ko-KR`;
- native slash evidence mode `native`;
- source protection and copy-audit rules;
- stage order and package version.

Changing the lock or checkpoint outside the engine invalidates every later stage.

## 5. Exact instruction traceability

1. Preserve every non-empty instruction line unchanged.
2. Connect every source line to at least one `REQ-*` ID.
3. Give every requirement acceptance checks and stage coverage.
4. Track each requirement through analysis, research where applicable, design, implementation, review, and test.
5. Require physical evidence and a verification method.
6. `partial`, `missing`, and `blocked` fail.
7. `not_applicable` requires a project-specific explanation and evidence.
8. Classify every omission as instruction, analysis, research, design, implementation, verification, reporting, or target mismatch.
9. A summary cannot replace the exact source instruction.

## 6. Exhaustive source analysis

1. Inventory every source file with path, size, kind, and SHA-256.
2. Produce one analysis finding for every inventoried path, including excluded or non-code paths.
3. Discover page candidates from routes, HTML files, framework pages, Android activities and fragments, XML layouts, iOS views, menus, navigation calls, modals, CRUD flows, authentication, administration, settings, and data models.
4. Record fields, actions, states, logic, security risks, performance risks, and design observations.
5. Sampling is not exhaustive analysis.
6. A file without a finding fails the analysis gate.

## 7. Dynamic page inventory

1. Do not hardcode universal required page names.
2. Build candidate pages from instructions, physical source files, routes, navigation, menus, models, and research.
3. Map every candidate to a `pageId` or exclude it with a detailed reason and physical evidence.
4. Store each page route or entry point, regions, fields, actions, states, origin, and required reason.
5. Keep the same page IDs across design, implementation, review, test, and screenshots.
6. Missing or unexplained candidates fail.

## 8. Direct source-body research

1. A search-result URL, title, or snippet is not evidence.
2. Retrieve the actual body through an implemented fetcher or physical native browser extraction.
3. Store URL, title, status, body path, body length, SHA-256, excerpt, retrieval timestamp, extraction mode, session evidence, freshness, and project-fit reason.
4. Reject empty bodies, access-denied pages, CAPTCHA pages, login walls, and placeholder pages.
5. Prefer current official documentation for platform-critical technologies.
6. Require official evidence for core platform integration.
7. Map every accepted finding to a feature, page, design decision, implementation path, and verification.
8. Do not copy external visual design or content verbatim.

## 9. Dynamic design decisions

1. Do not hardcode a fixed concept, palette, template, site, or page set.
2. Derive design research queries from the current instructions and page inventory.
3. Store `designTokenProvenance`, decision reasons, and source evidence.
4. Reject manual concept pickers or fixed presets unless the user explicitly supplied a brand system.
5. Tailor information density, trust, friendliness, persuasion, and workflow ergonomics to the current audience, especially small-business users.

## 10. Design, implementation, and verification are separate gates

### 10.1 Design owner

Before implementation, produce:

- one unique visual mockup per page;
- an all-page comparison board;
- hero or first-viewport strategy;
- image, icon, typography, and color strategies;
- regions, fields, actions, navigation, and all required states;
- motion storyboard with trigger, duration, easing, purpose, and reduced-motion behavior;
- responsive and accessibility plans.

### 10.2 Implementation owner

Implement the design in physical files:

- real images or generated bitmap assets where required;
- hero or strong first-viewport signals where applicable;
- icons, typography, color, layout, responsive behavior, and accessibility;
- loading, empty, error, success, permission, offline, and restricted states;
- purposeful motion and reduced-motion code;
- actual data, logic, routes, and native bridges.

Declarations, gradients described as images, or mockups stored without implementation do not count.

### 10.3 Independent review owner

Use actual screenshots and independent semantic review to compare every page against the mockup and contract. Verify visual quality, content hierarchy, images, hero, motion, reduced motion, Korean text, states, responsiveness, accessibility, overlap, fields, logic, and functions. Browser automation may collect measurements but cannot self-approve semantic quality.

## 11. End-to-end traceability

The following chains must be complete:

- `requirementId`: source -> analysis -> design or implementation -> review -> test;
- `pageId`: candidate -> inventory -> mockup -> implementation -> screenshot -> visual review;
- `fieldId`: source -> page position -> data path -> validation -> test;
- `logicId`: trigger -> input -> processing -> output -> failure states -> code -> test;
- `featureId`: source body -> adoption reason -> page -> code -> runtime verification;
- `imageId`: purpose -> asset -> location -> source or generation prompt -> license -> screenshot;
- `motionId`: storyboard -> code -> reduced motion -> runtime verification.

Any broken required chain fails its owning stage.

## 12. Copy audit

1. Compare all analysis-source hashes with all output files, including `legacy`, unused, generated, and unreferenced directories.
2. Classify every exact copy as required runtime, required bridge, justified reference, forbidden bulk copy, or unexplained copy.
3. Reject bulk copies of old activities, fragments, view models, or layouts into a WebView result.
4. Store reference-only material under `.kh_aw/reference`, not the product source tree.
5. Require role and reason for every allowed copy.

## 13. Target-specific implementation

### 13.1 Android WebView app

Require Android project recognition, a physical WebView entry point, packaged HTML/CSS/JavaScript/images, a minimal justified native bridge, Android Studio or Gradle build evidence, and APK-content inspection. Legacy native screens cannot substitute for the HTML UI.

### 13.2 Responsive web

Require real entry points and routes, responsive mobile and desktop behavior, physical browser execution, screenshots, accessibility, Lighthouse, visual regression, and inspection of deployable build output.

### 13.3 Native and cross-platform targets

Require actual platform build and runtime evidence. Cross-platform projects must pass every applicable target gate; one side cannot substitute for the other.

## 14. Independent Codex workers

1. Calculate 2-60 workers from current project complexity for every stage.
2. Require each planned worker and task to have a unique Codex session.
3. Verify a physical Codex rollout JSONL path, session ID, task ID, event count, and SHA-256.
4. Store a physical output with a unique SHA-256 for every worker.
5. Require at least one cross-review and reject duplicate worker outputs.
6. Require a separate lead session to read and accept all required workers.
7. Reject self-authored inventories or invocation receipts as proof of independent work.

## 15. Native slash capability enforcement

1. Every stage requires native `/goal` and `/agents` evidence.
2. Intake additionally requires `/plan`.
3. Analyze requires `/context` and `/artifact`.
4. Research requires `/search` and `/artifact`.
5. Design requires `/plan` and `/artifact`.
6. Implement requires `/diff`.
7. Review requires `/review` and `/diff`.
8. Test requires `/test`.
9. Release requires `/artifact` and `/diff`.
10. Store the actual invocation, physical output, output hash, and Codex session ID.
11. A required slash capability never passes through fallback or a text claim.
12. When the Codex surface cannot expose required native evidence, report `blocked` or `failed`, not completion.

## 16. Tool and runtime evidence

Every required tool execution stores command, version, start and end times, exit code, log, log hash, artifact paths, artifact hashes, and owning requirement IDs. A reserved tool ID cannot be satisfied by an unrelated command. Required commands that were not run remain `not_run` and fail.

APK installation commands are forbidden. Build, lint, unit test, screenshot test, emulator or simulator state, Logcat, browser E2E, accessibility, Lighthouse, and visual regression are selected by target and actual project features.

## 17. Language boundary

1. Codex-facing plugin metadata, prompts, skills, policies, contracts, ledgers, assignments, repair tickets, gate errors, and internal reports are English.
2. Exact user instructions and direct quoted source bodies may remain in their original language as immutable evidence.
3. IDE panel guidance intended for the user is Korean.
4. Product names, labels, buttons, forms, errors, empty states, and in-product AI conversation or output are Korean.
5. Internal artifacts containing Hangul, CJK mojibake, replacement characters, or common broken-encoding markers fail unless located in an explicitly allowed raw-user-text field.
6. A Korean-targeted product with no Korean UI source and runtime evidence fails.

## 18. Security and publication

1. Never publish cookies, login databases, browser profiles, tokens, passwords, `.env`, private user data, run logs, build caches, or personal project output.
2. Enforce ignore rules and scan publication files.
3. Do not package a complete private analysis-source copy.
4. Do not use assets, fonts, or icons without documented license evidence.
5. Prefer free or already available tools unless the user explicitly approves paid dependencies.

## 19. Session forensics

Parse the physical Codex rollout JSONL. Record commands, failed commands, file changes, slash invocations, test and browser execution, target artifact inspection, source hash, event count, parse errors, and differences between the final claim and physical evidence. A self-reported session summary does not pass.

## 20. Repair ownership

Classify each omission as `instruction_miss`, `analysis_miss`, `research_miss`, `design_miss`, `implementation_miss`, `verification_miss`, `reporting_miss`, or `target_mismatch`. Return repair to the earliest owning stage, execute a physical change, rerun the actual tool or gate, and close the ticket only with new evidence. Repeated identical failures must change strategy.

## 21. Completion definition

Completion is true only when:

- all eight current gate reports have exact `passed` truth and matching hashes;
- every stage has an exact passed status;
- run lock and checkpoint are current;
- all requirements and dynamic pages are covered;
- the analysis source is unchanged;
- copy audit has no forbidden or unexplained copy;
- research contains valid direct bodies and current official sources where required;
- design, implementation, screenshots, independent review, and target tests all pass;
- required native slash and worker session evidence is physical and valid;
- internal evidence is English and actual product UI is Korean;
- no required item is `failed`, `blocked`, `not_run`, `partial`, or `missing`;
- no repair ticket remains open; and
- the engine has created and revalidated `release/release-receipt.json`.

An AI statement such as "completed" is not completion evidence.
