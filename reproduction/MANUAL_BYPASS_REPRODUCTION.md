# Manual Bypass Reproduction

## Physical session

Session:

`C:/Users/pyun7/.codex/sessions/2026/07/24/rollout-2026-07-24T22-11-56-019f9441-02f7-7d52-9535-803597d437cf.jsonl`

Working directory: `C:/testAPP`

The session invoked the cache `3.2.0` CLI with a cache plugin root and a marketplace
root. Doctor reported the folder mismatch, absent marketplace files beside the cache,
package mismatches, and missing distribution files. The following assistant message
acknowledged that doctor failed and continued the work manually.

## Why the bypass was possible

1. Doctor combined unrelated plugin, marketplace, package, and distribution concerns.
2. The skill procedure described doctor as startup guidance, not a machine-enforced
   transition that owned every later stage.
3. Six entry skills allowed a later procedure to be selected without one authoritative
   state controller.
4. Final session analysis collected claims but did not bind every claim to evidence.

## Redesign response

- One public entrypoint.
- Categorized doctor output with expected, actual, repair, and reverify fields.
- Plugin-only doctor independent from marketplace/distribution.
- Project-owned state and runtime with explicit resume.
- Capability evidence and claim-evidence bindings.
- Failed gates remain nonterminal and generate issue-specific repair tickets.

The historical session itself is not altered. It remains the regression fixture.
