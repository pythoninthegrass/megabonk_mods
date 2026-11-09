---
id: TASK-032.09
title: >-
  Require a type on the MCP interact tool so it cannot hit an arbitrary nearby
  interactable
status: Done
assignee: []
created_date: '2026-11-05T20:40:00Z'
updated_date: '2026-11-05 21:19'
labels: []
dependencies: []
references:
  - scripts/mcp_server.py
  - docs/development.md
parent_task_id: TASK-032
priority: low
ordinal: 168000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The MCP `interact` tool accepts no `type`, in which case the harness activates the nearest interactable of any kind. During a from-scratch level check this hit the boss spawner three times in one session and summoned an unwanted boss each time, because the spawner was the nearest interactable and an agent expected a different target. An untyped call has side effects the caller rarely intends, and the failure is silent: the call succeeds and reports the interactable it picked.

Scope is the MCP layer only (`scripts/mcp_server.py`); `run.py interact` and the harness verb keep their current behaviour. The MCP server must be restarted to pick up a changed tool signature.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The MCP interact tool requires a type and fails with a clear tool error, before anything is sent to the game, when it is missing or empty
- [x] #2 A call with a type behaves exactly as before, including max_distance and force
- [x] #3 run.py interact and the harness interact verb are unchanged
- [x] #4 A test written first fails on the old signature and passes on the new one
- [x] #5 docs/development.md and the tool docstring describe the required type and show no untyped interact example; task check passes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first in tests/test_mcp_server.py: drop the untyped `interact {}`, `max_distance`-only and `force`-only rows from INPUT_TOOL_CASES and add typed variants (`type` + `max_distance`, `type` + `force`); add a test that `interact` with no type, `type=""` and whitespace-only type returns a tool error and writes nothing to the harness queue. Run: the new tests fail on the old signature.
2. scripts/mcp_server.py: change the signature to `interact(type: str, max_distance=None, force=False)`; raise ToolError("interact: type is required ...") on an empty or blank type before calling _command. Update the docstring.
3. docs/development.md: change `interact(type?, ...)` to `interact(type, ...)` (line 181) and note the required type; the harness verb and run.py rows stay as is. Check that line 697 and the "Interactables" section show no untyped MCP example.
4. Run the new tests, `task scripts:test`, `task check`. run.py and the C# harness untouched.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The MCP `interact` tool now requires `type`. An absent, empty or whitespace-only type raises a ToolError before anything is written to the harness queue. Typed calls, including max_distance and force, send the same payload as before. `run.py interact` and the harness verb are unchanged. Tests: the untyped rows were replaced with typed variants and a parametrized test covers the three refusal cases; it failed on the old signature and passes now. docs/development.md and the tool docstring describe the required type. `task check` passes. The MCP server must be restarted to pick up the new signature.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
