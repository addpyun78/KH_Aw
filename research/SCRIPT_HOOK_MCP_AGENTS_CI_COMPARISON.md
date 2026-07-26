# Script, Hook, MCP, Agent, and CI Comparison

## Scripts

Public implementations use scripts for deterministic parsing, package operations, and
repeatable validation. KH_Aw retains its Python/Node engine and adds separate modules
for installation resolution, doctor categories, runtime bootstrap, requirements,
reachability, task graph, claims, versions, and deterministic packaging.

## Hooks

Hooks are useful for lifecycle capture but require user trust and are not uniformly
available. KH_Aw therefore records gate events itself and treats plugin hooks as an
optional enhancement, not a required completion mechanism.

## MCP and apps

Figma, Notion, GitHub, and Codex Security show that MCP/app declarations belong in
plugin metadata when the plugin owns an external integration. KH_Aw orchestrates the
active Codex tools and does not invent an MCP server solely to simulate evidence.

## Agents

A Team and Process Jobs demonstrate explicit agent roles and testable receipts. KH_Aw
keeps dynamic independent workers but validates physical delegation and aggregation
instead of requiring a non-existent `/agents` command.

## CI

Public community plugins commonly test hooks, scripts, and installation assumptions.
KH_Aw CI must cover source checkout, versioned cache, CRLF conversion, duplicate cache,
single skill visibility, runtime resume, deterministic ZIP, and package doctor.
