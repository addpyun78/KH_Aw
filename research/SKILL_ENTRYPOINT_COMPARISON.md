# Skill Entrypoint Comparison

| Pattern | Public examples | Strength | Failure risk | KH_Aw decision |
|---|---|---|---|---|
| One focused skill | Remotion, Tailtest, BringYour MCP | Clear invocation | Can become too large | One public `kh-aw` entry plus internal workflow references |
| Several independent skills | Figma, Expo, Codex Security | Good for unrelated tasks | Competing stage definitions | Not suitable for one end-to-end engine |
| Commands plus agents | A Team | Explicit dispatch | Surface-specific commands may drift | Keep capability dispatch in runtime contracts |
| Script-heavy skills | Process Jobs, Codex Security | Deterministic checks | Cache-relative script coupling | Copy versioned scripts into project runtime |

Before redesign, six KH_Aw skills separately described audit, full cycle, research,
implementation, orchestration, and release. Their overlapping start conditions made it
possible to skip the intended top-level flow. The redesigned package exposes only
`skills/kh-aw/SKILL.md`; prior procedures are preserved under `references/workflows/`.
