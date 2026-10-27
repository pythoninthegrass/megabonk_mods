---
id: TASK-018
title: Add MCP tools for save/reload verification and editor widget targeting
status: To Do
assignee: []
created_date: '2026-10-27T07:23:00Z'
labels:
  - dev-harness
  - tooling
dependencies: []
references:
  - scripts/mcp_server.py
  - scripts/run.py
  - tests/test_mcp_server.py
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
documentation:
  - docs/development.md
  - AGENTS.md
priority: medium
type: enhancement
ordinal: 74000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Driving the editor through the megabonk MCP tools is slow and error-prone when verifying a save/reload loop. During an offline check (TASK-016 AC#4) the gaps were: there is no tool to locate the harness command folder or the custom-level save directory, so paths had to be hand-typed; `load` returns before the level is armed and there is no synchronous log wait, so agents fall back to sleeping; a bad key name silently no-ops instead of erroring; `state` does not report the edit count or save status, so dirty/saved state had to be read from a screenshot and the log; and every mouse interaction needs guessed screenshot pixel coordinates, so a click meant for the Save toolbar hit the terrain instead. These additions make the save/reload loop verifiable and the editor targetable without that guessing. The work splits into offline-testable MCP helpers (no game needed, do first) and game-tested editor tools; see the subtasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 An agent can locate the game directory, harness folder, latest log path and custom-level save directory without shelling out to a script.
- [ ] #2 An agent can wait on a log line (log_wait) and gets a tool error on a bad key instead of a silent no-op.
- [ ] #3 `state` reports the edit count and save status so a save is verifiable without reading the screenshot or the log.
- [ ] #4 Editor widgets can be targeted by name and levels saved/listed without guessing screenshot pixel coordinates.
- [ ] #5 All additions are tested and documented in docs/development.md.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
