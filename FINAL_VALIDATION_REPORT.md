# KH_Aw 4.0.0 Validation Report

## Verified locally

- 15 public plugin implementations recorded with URLs and commits.
- Actual historical doctor failure and manual continuation traced to a physical session.
- Source plugin doctor and repository distribution doctor passed during redesign.
- Versioned-cache, CRLF checkout, duplicate-shadow, and deterministic-ZIP cases passed.
- Regression suite passed after the first full implementation pass.
- One visible source skill named `kh-aw`.
- GitHub `kh-aw-marketplace` publication: commit `f58fe40`.

## Conditions still open

- Install the resulting archive through the supported Codex plugin manager.
- Open a new session and invoke `@kh-aw` directly.
- Run a complete eight-stage real project through release receipt.
- Reinstall with an older cache retained and repeat the full Codex E2E.

The plugin-management install operation was not exposed in this environment, and direct
execution of the Windows app `codex.exe` returned `Access is denied`. The exact
40-condition status is in `COMPLETION_CRITERIA_LEDGER.md`; open conditions are not
converted into passes.
