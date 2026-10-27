---
id: TASK-020
title: >-
  Cut the rebuild-and-relaunch loop when probing the live game through the MCP
  server
status: Done
assignee: []
created_date: '2026-10-27T20:06:00Z'
updated_date: '2026-10-27T21:29:00Z'
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
- [x] #1 Every subtask is Done
- [x] #2 The Hell diagnosis (which MapData assets exist and their eMap values) can be repeated through MCP tools alone, with no mod rebuild
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
All five subtasks are Done: query_objects with jq filtering (020.01), map/stage/tier/seed overrides on load and relaunch (020.02), the failing log line in the relaunch error (020.03), regex filtering on log_tail (020.04) and TOON result encoding (020.05). The Hell diagnosis is repeatable through MCP tools alone: `query_objects(type="MapData", fields=["eMap"])` on the running game lists MapDesert=2, MapDungeon=16, MapForest=1, MapGraveyard=8, MapHell=64 with no mod rebuild. task check passed at the last subtask (276 tests).
<!-- SECTION:FINAL_SUMMARY:END -->
