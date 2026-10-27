---
id: TASK-020
title: >-
  Cut the rebuild-and-relaunch loop when probing the live game through the MCP
  server
status: To Do
assignee: []
created_date: '2026-10-27T20:06:00Z'
labels:
  - mcp
  - dev-harness
dependencies: []
references:
  - 'https://github.com/mwilliamson/jq.py'
priority: medium
type: enhancement
ordinal: 80000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Diagnosing TASK-007.05.02 (Hell would not load) took two mod rebuilds and relaunches, one of which sat for the full timeout, only to learn which MapData assets exist in the running game and that MapHell holds eMap=64 while the Il2Cpp dump says 4. Agents also hand-wrote and deleted a patched level file just to change the map, and `relaunch` reported a load failure without the reason. This parent groups the harness and MCP improvements that remove those costs: a generic live-object query with jq filtering, level override arguments, the failure line in the relaunch error, and a filtered log read. Related closed work: TASK-010.06 (MCP server), TASK-018 (save/reload verification tools).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every subtask is Done
- [ ] #2 The Hell diagnosis (which MapData assets exist and their eMap values) can be repeated through MCP tools alone, with no mod rebuild
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
