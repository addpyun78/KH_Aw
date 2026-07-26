# Official Codex Plugin Model

Research date: 2026-07-26

## Discovery and installation

- A plugin is rooted by `.codex-plugin/plugin.json`.
- Codex CLI installs plugins through `/plugins`; a new session is required after installation.
- A plugin can package skills, MCP configuration, app configuration, hooks, assets,
  agents, and other supporting resources.
- Skills use progressive disclosure: Codex first sees name and description, then loads
  the selected `SKILL.md` and referenced resources.
- `AGENTS.md` files are layered from repository root toward the current directory and
  have a combined size limit.
- Available slash commands vary by Codex surface. A plugin must require capabilities,
  not invent unsupported slash command names.
- Hooks are deterministic lifecycle scripts and require explicit trust.

## KH_Aw design consequences

1. Expose one `kh-aw` skill and keep stage procedures as internal references.
2. Resolve the physical plugin root independently from repository and version-cache roots.
3. Separate plugin doctor, installation doctor, project doctor, and distribution audit.
4. Copy a versioned runtime into the project workspace so a cache update cannot alter an
   active run.
5. Accept native Codex evidence when available and physical tool/subagent evidence for
   the same behavior when a slash command is unavailable.
6. Keep exact user instructions, task graph, state, repair history, and evidence outside
   the installed cache.

## Primary sources

- https://developers.openai.com/codex/plugins
- https://developers.openai.com/codex/skills
- https://developers.openai.com/codex/guides/agents-md
- https://developers.openai.com/codex/subagents
- https://learn.chatgpt.com/codex/hooks
- https://learn.chatgpt.com/codex/reference/slash-commands
- https://developers.openai.com/plugins/build/plugins
- https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/plugin-creator/references/plugin-json-spec.md
