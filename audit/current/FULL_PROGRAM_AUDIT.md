# Current KH_Aw Full Program Audit

Audit time: 2026-07-26

## Scope

The current repository was enumerated after excluding generated `.git`, Python cache,
pytest cache, `node_modules`, and build/runtime directories. The resulting physical
program inventory contains 125 files and 2,614,532 bytes:

- `audit/current/inventory.jsonl`: one row per file with path, size, hash, type, and lines
- `audit/current/inventory.csv`: the same inventory for spreadsheet review
- `audit/current/inventory-summary.json`: counts and root

The previous `audit/ORIGINAL_*` files describe an older A2A archive and are retained as
historical evidence; they are not used as the current KH_Aw inventory.

## Execution chain

`kh_aw_cli.py` owns command parsing and delegates to modules under `scripts/kh_aw/`.
New work flows through `init`; existing work through `resume`. Both lead to the same
eight stage state and gate chain. `finalize` can create a receipt only after clean stage
reports. `doctor`, `project-doctor`, `verify-run`, and `e2e` are independent checks.

## File groups reviewed

- Plugin/marketplace metadata and user documents
- Six former skills and their agent metadata
- CLI and 21 original Python engine modules
- Four Node runtime verification scripts
- Six JSON schemas
- Python regression suite and CI workflow
- Package and release hash ledgers
- Historical audit/final reports
- Six visual assets

## Root causes found

1. Version cache folders were rejected because the leaf was compared with plugin ID.
2. Raw-byte hashes treated Git CRLF conversion as content tampering.
3. Plugin doctor demanded marketplace and repository distribution files in a cache.
4. Six public skills competed to own one workflow.
5. Fixed slash command names exceeded the active official command surface.
6. App/web target inference omitted Codex plugins.
7. Runtime depended on the installation path and lacked an explicit resume controller.
8. Requirements were one-line copies without semantic class or task dependencies.
9. File candidates did not establish entrypoint/import/route reachability.
10. Repair history counted repeats without issue category evidence.
11. Final claims were collected but not sentence-to-evidence verified.
12. Version text and final reports drifted between 3.2.0 and 3.2.1.
13. Existing reports could pass synthetic session-shaped JSONL.
14. Schemas allowed empty physical test arrays and inconsistent orchestration examples.
15. Existing current-package audit claims actually referred to an older A2A source.

## Compatibility decision

The eight stages, existing command names, function signatures, app/web gates, analysis
protection, tool evidence, and independent worker ledger remain. New behavior is added
as owner modules and CLI commands. This limits changes to the failing boundaries while
preserving existing callers.
