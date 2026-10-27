---
id: TASK-020.03
title: Include the failing log line in the relaunch error
status: To Do
assignee: []
created_date: '2026-10-27T20:07:00Z'
labels:
  - mcp
  - dev-harness
dependencies: []
parent_task_id: TASK-020
priority: low
type: enhancement
ordinal: 83000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`relaunch` now stops early when a level fails to load, but its error only says to look in the game log. An MCP caller then needs a second call to learn the reason (for example `no MapData found for map=32; available: ...`). Returning the matched line in the error saves that round trip.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 When relaunch stops on `LevelLoader: load failed` or `EditorMode: unsupported map`, the error passed to the caller includes the full matching log line, not only the fixed hint
- [ ] #2 The MCP `relaunch` tool error contains the same line
- [ ] #3 A relaunch that succeeds, or times out without a matching line, is unchanged
- [ ] #4 The log-line extraction has offline unit tests, including a log with several matching lines (the one after the last `DevHarness: enabled` is used)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
