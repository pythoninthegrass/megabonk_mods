---
id: TASK-020.04
title: Filter log_tail by regex
status: In Progress
assignee:
  - Claude
created_date: '2026-10-27T20:07:00Z'
updated_date: '2026-10-27T21:26:00Z'
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
- [x] #1 The MCP `log_tail` tool accepts an optional regex pattern and returns only matching lines, up to the requested line count of matches
- [x] #2 An optional since_launch flag (default true, as in `log_wait`) limits results to lines after the last `DevHarness: enabled`
- [x] #3 An invalid regex is a tool error naming the parse failure
- [x] #4 Without a pattern the output is unchanged
- [x] #5 Filtering has offline unit tests
- [x] #6 Documented in docs/development.md
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add failing tests: invalid regex is a tool error; max_lines caps matches.
2. Share regex compile and session-line reading between log_tail and log_wait; log_tail raises ToolError on a bad pattern.
3. Update the log_tail paragraph in docs/development.md.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
log_tail already accepted pattern and since_launch; this adds the invalid-regex tool error ("log_tail: invalid pattern ...: <parse failure>"), moves regex compilation and session-line reading into helpers shared with log_wait, adds tests for the invalid regex and for max_lines capping matches, and updates docs/development.md. task check passes (276 tests).
<!-- SECTION:FINAL_SUMMARY:END -->
