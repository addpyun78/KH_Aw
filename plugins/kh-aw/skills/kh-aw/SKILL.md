---
name: kh-aw
description: Audit, design, implement, repair, resume, verify, and release any Codex development project through one evidence-gated entrypoint.
---

# KH_Aw

Use this single entrypoint for every KH_Aw request. Preserve the user's exact
instructions and determine the project type from instructions plus physical files.

## Required startup

1. Run `python scripts/kh_aw_cli.py doctor --plugin-root .`.
2. Run `python scripts/kh_aw_cli.py installation-status`.
3. For a new run, call `init --target-auto`. For an existing run, call `resume`.
4. Read `contract/requirements.json`, `contract/task-graph.json`, and
   `inventory/source-reachability.json` before implementation.

## Execution rules

- Treat analysis sources as read-only and keep product/runtime output separate.
- Use available Codex tools and subagents by capability. Do not require a slash
  command that the active surface does not expose.
- Keep every exact instruction line linked to a requirement, ticket, verification,
  and physical evidence.
- Repair the owner module and change strategy when a failure signature repeats.
- Bind every final claim to files, hashes, commands, tests, or a real Codex session.
- Do not report a terminal result while any gate is failed, blocked, not run, or
  supported only by prose.

Detailed internal workflows live under `references/workflows/`; they are references,
not separately exposed entrypoints.
