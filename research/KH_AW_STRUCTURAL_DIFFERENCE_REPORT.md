# KH_Aw Structural Difference Report

## Before

- Six public skills with overlapping stage ownership.
- App/web-only target inference.
- Monolithic doctor requiring a complete marketplace beside every plugin cache.
- Plugin root leaf forced to equal `kh-aw`.
- Raw-byte-only package hashes.
- Fixed unsupported slash names.
- No explicit installation resolver, runtime snapshot, resume command, semantic
  requirement compiler, source graph, ticket dependency graph, or claim verifier.

## Redesigned structure

- One public `kh-aw` skill; six prior procedures retained as internal references.
- `codex-plugin` target and project-specific tool policy.
- Plugin doctor separated from optional marketplace/distribution checks.
- Source and versioned-cache root shapes accepted.
- Raw and normalized-LF integrity records.
- Capability evidence independent from slash command spelling.
- Project-owned versioned runtime and explicit `resume`.
- Semantic requirement fields, task tickets, reachability graph, installation/shadow
  inventory, claim bindings, version ledger, and deterministic ZIP builder.

## Compatibility boundary

Existing CLI commands and stage names remain available. New behavior is added through
modules and new commands. Existing app/web gates remain in place for their target types.
