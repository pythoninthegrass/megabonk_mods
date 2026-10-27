---
id: TASK-020.04
title: Filter log_tail by regex
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
ordinal: 84000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The game log is long and mostly noise for a given question. Diagnosing the Hell load needed only the `LevelLoader` and `EditorMode` lines, and the shell was used to filter them because `log_tail` returns unfiltered lines. A regex filter on `log_tail` lets MCP-only agents get them directly, matching what `log_wait` already does for waiting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The MCP `log_tail` tool accepts an optional regex pattern and returns only matching lines, up to the requested line count of matches
- [ ] #2 An optional since_launch flag (default true, as in `log_wait`) limits results to lines after the last `DevHarness: enabled`
- [ ] #3 An invalid regex is a tool error naming the parse failure
- [ ] #4 Without a pattern the output is unchanged
- [ ] #5 Filtering has offline unit tests
- [ ] #6 Documented in docs/development.md
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
