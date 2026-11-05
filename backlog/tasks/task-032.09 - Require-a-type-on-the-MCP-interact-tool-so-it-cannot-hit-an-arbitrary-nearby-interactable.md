---
id: TASK-032.09
title: >-
  Require a type on the MCP interact tool so it cannot hit an arbitrary nearby
  interactable
status: To Do
assignee: []
created_date: '2026-11-05T20:40:00Z'
labels: []
dependencies: []
references:
  - scripts/mcp_server.py
  - docs/development.md
parent_task_id: TASK-032
priority: low
type: enhancement
ordinal: 168000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The MCP `interact` tool accepts no `type`, in which case the harness activates the nearest interactable of any kind. During a from-scratch level check this hit the boss spawner three times in one session and summoned an unwanted boss each time, because the spawner was the nearest interactable and an agent expected a different target. An untyped call has side effects the caller rarely intends, and the failure is silent: the call succeeds and reports the interactable it picked.

Scope is the MCP layer only (`scripts/mcp_server.py`); `run.py interact` and the harness verb keep their current behaviour. The MCP server must be restarted to pick up a changed tool signature.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The MCP interact tool requires a type and fails with a clear tool error, before anything is sent to the game, when it is missing or empty
- [ ] #2 A call with a type behaves exactly as before, including max_distance and force
- [ ] #3 run.py interact and the harness interact verb are unchanged
- [ ] #4 A test written first fails on the old signature and passes on the new one
- [ ] #5 docs/development.md and the tool docstring describe the required type and show no untyped interact example; task check passes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
