# Skill Visibility Report

## Installed cache snapshot

The current machine cache exposes:

1. `kh-aw-audit-upgrade`
2. `kh-aw-full-cycle`
3. `kh-aw-implementation-repair`
4. `kh-aw-multi-agent-orchestration`
5. `kh-aw-release-company`
6. `kh-aw-research-design`

This is stale package evidence and is not treated as an active-install confirmation.

## Redesigned package

The workspace package exposes only:

`plugins/kh-aw/skills/kh-aw/SKILL.md`

The six former `SKILL.md` procedures remain under `references/workflows/` so their
rules are retained without becoming competing public entrypoints. `doctor` fails the
skill-visibility category unless exactly one visible skill named `kh-aw` exists.

## Fresh-session check still required

Official plugin behavior requires a new session after installation. A supported
plugin-manager install and fresh-session `@kh-aw` invocation have not yet been executed
against this unpublished workspace state, so that external condition remains open.
