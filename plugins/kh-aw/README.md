# KH_Aw Codex Plugin 4.0.0

- Plugin ID: `kh-aw`
- Public skill: `skills/kh-aw/SKILL.md`
- Project types: web, WebView, Android, iOS, cross-platform, and Codex plugin
- Independent workers: dynamic 2-60
- APK installation: forbidden

## Engine modules

The existing eight-stage gate engine remains. Added owner modules cover installation
resolution, categorized doctor checks, versioned runtime bootstrap, resume, semantic
requirements, source reachability, task graphs, issue classification, independent
verification, claim verification, version consistency, deterministic packaging, and
local cache/CRLF/shadowing E2E.

## Commands

```text
doctor                 validate plugin; add --distribution for repository checks
installation-status    show cache versions, duplicates, and selected candidate
init                    create a project-owned run
resume                  continue the earliest incomplete stage
project-doctor          validate state, runtime, graph, and reachability
prepare-agents          calculate independent worker assignments
record-subagent         bind physical Codex worker evidence
advance                 verify and move one stage
verify-run              independently compare gates, requirements, and receipt
finalize                create a release receipt only after clean gates
build-package           build and hash-check a deterministic ZIP
e2e                     test version cache, CRLF, shadowing, and ZIP repeatability
```

Native Codex commands are used when the active surface supports them. Otherwise, the
same behavior must be proven by physical tool or subagent evidence; prose is never
accepted as evidence.
