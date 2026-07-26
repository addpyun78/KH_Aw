# KH_Aw Redesigned Architecture

## Components

1. **Plugin entrypoint**: one `skills/kh-aw/SKILL.md` selects new or resumed work.
2. **Installation resolver**: inventories source, marketplace, and versioned cache roots;
   reports duplicates and shadowing.
3. **Plugin doctor**: validates manifest, package integrity, and skill visibility.
4. **Project doctor**: validates run state, runtime snapshot, requirement graph, and
   source reachability.
5. **Requirement compiler**: preserves each exact non-empty instruction line and adds
   semantic classes, negative constraints, evidence needs, tickets, and checks.
6. **Source reachability analyzer**: records entrypoints, imports, and route-like links.
7. **Task graph**: links every requirement to a ticket with dependencies, input,
   output, verification, retry policy, and state.
8. **Versioned project runtime**: copies executable engine scripts to
   `.kh_aw/runtime/<version>` and hashes every file.
9. **Stage controller**: retains intake, analyze, research, design, implement, review,
   test, and release gates.
10. **Repair controller**: classifies failures, retains strategy history, and changes
    strategy generation for repeats.
11. **Independent verifier and claim verifier**: compare state, gates, receipts, and
    final sentences with physical evidence.
12. **Package builder**: generates raw/normalized integrity records and deterministic ZIP.

## Data flow

`exact instructions -> semantic requirements -> task graph -> inventory/reachability ->`
`research evidence -> design -> implementation -> review -> tests -> claim verification ->`
`release receipt`

Every arrow is a stored file relation, not only a prompt instruction.

## Security boundaries

- Analysis roots are read-only and physically snapshotted.
- Product files, KH_Aw state, and installed plugin cache are separate roots.
- Project runtime files are hashed and immutable for one run version.
- Commands retain cwd, exit code, stdout/stderr log, hashes, and artifacts.
- A plugin cache is never edited to manufacture a pass.

## Recovery flow

`resume` loads the existing run, keeps repair history, selects the earliest incomplete
stage, records a resume event, and continues with the versioned runtime. It does not
create a new task merely because the Codex session changed.

## System and AI responsibility

The system calculates counts, paths, hashes, state transitions, missing links, command
results, and evidence bindings. AI performs semantic analysis, research interpretation,
design judgment, code changes, repair strategy, and independent quality review.
