# KH_Aw Codex Marketplace Plugin 4.0.0

`KH_Aw` is a reusable, evidence-gated Codex development workflow. It preserves exact
instructions, inventories an existing project, researches public sources, plans work,
coordinates independent reviewers, implements changes, repairs failures, resumes after
interruption, verifies claims, and packages a release.

## Redesigned control path

```text
@kh-aw
  -> plugin doctor and installation inspection
  -> init or resume
  -> semantic requirements and task graph
  -> full inventory and source reachability
  -> research, design, implementation
  -> independent review and actual tests
  -> claim verification and release receipt
```

Only `skills/kh-aw/SKILL.md` is public. Prior stage procedures remain in
`plugins/kh-aw/references/workflows/`.

## Main commands

Run from this repository:

```powershell
python plugins/kh-aw/scripts/kh_aw_cli.py doctor --plugin-root plugins/kh-aw
python plugins/kh-aw/scripts/kh_aw_cli.py doctor --plugin-root plugins/kh-aw --marketplace-root . --distribution
python plugins/kh-aw/scripts/kh_aw_cli.py installation-status
python plugins/kh-aw/scripts/kh_aw_cli.py e2e --plugin-root plugins/kh-aw
python plugins/kh-aw/scripts/kh_aw_cli.py build-package --plugin-root plugins/kh-aw
```

Project runs add `init`, `resume`, `project-doctor`, `advance`, `verify-run`, and
`finalize`.

## Evidence boundaries

- Unsupported slash commands are not hard dependencies.
- Physical tools and independent Codex subagents must provide files, receipts, logs,
  session identities, hashes, and review links.
- Analysis sources are protected read-only.
- The runtime is copied and hashed under each project workspace.
- Failed, blocked, missing, or not-run checks cannot become a terminal result.

Research, reproduction, architecture, criteria, and beginner documents are under
`research/`, `reproduction/`, `design/`, `COMPLETION_CRITERIA_LEDGER.md`, and `docs/`.
