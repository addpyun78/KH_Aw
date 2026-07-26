# Reproduction Matrix

| ID | Environment | Action | Before redesign | Redesigned source result |
|---|---|---|---|---|
| R1 | Repository checkout | plugin doctor | Passed only from expected source layout | Passed |
| R2 | Codex cache `kh-aw/3.2.1` | plugin doctor | Folder-name false failure | Versioned root accepted |
| R3 | Git `core.autocrlf=true` | package integrity | Most text files reported modified | Normalized-LF verification passed |
| R4 | Plugin-only cache | doctor without marketplace | Missing marketplace/distribution errors | Plugin checks run independently |
| R5 | Multiple cache roots | installation inspection | No explicit shadow report | Duplicate version grouped and flagged |
| R6 | Skill discovery | inspect visible skills | Six competing public entrypoints | One `kh-aw` entrypoint |
| R7 | Unsupported slash names | intake capability policy | Required `/agents`, `/context`, `/artifact`, `/test` | Physical capability evidence accepted |
| R8 | Interrupted run | restart process | Implicit latest state only | Explicit `resume` with history retention |
| R9 | Repeated package build | ZIP twice | No deterministic builder | Identical SHA-256 |
| R10 | Past failed Codex session | doctor then continue manually | Manual bypass possible | Failure remains categorized and nonterminal |

The local E2E command executed R2, R3, R5, and R9 with temporary physical copies:

`python plugins/kh-aw/scripts/kh_aw_cli.py e2e --plugin-root plugins/kh-aw`

Result on 2026-07-26: four cases passed. This is local engine evidence, not a claim
that GitHub publication and a fresh post-install Codex session have been executed.
