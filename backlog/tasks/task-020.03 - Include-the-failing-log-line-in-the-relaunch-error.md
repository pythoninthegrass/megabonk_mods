---
id: TASK-020.03
title: Include the failing log line in the relaunch error
status: Done
assignee: []
created_date: '2026-10-27T20:07:00Z'
updated_date: '2026-10-27T21:21:00Z'
labels:
  - mcp
  - dev-harness
dependencies: []
modified_files:
  - scripts/run.py
  - tests/test_run.py
  - tests/test_mcp_server.py
  - docs/development.md
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
- [x] #1 When relaunch stops on `LevelLoader: load failed` or `EditorMode: unsupported map`, the error passed to the caller includes the full matching log line, not only the fixed hint
- [x] #2 The MCP `relaunch` tool error contains the same line
- [x] #3 A relaunch that succeeds, or times out without a matching line, is unchanged
- [x] #4 The log-line extraction has offline unit tests, including a log with several matching lines (the one after the last `DevHarness: enabled` is used)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first in tests/test_run.py: `log_line_containing(log, marker)` returns the full first matching line after the last `DevHarness: enabled` (several matches, older session, no match, missing file); relaunch errors for load-failed and unsupported-map append the line; success and timeout paths unchanged.
2. Add `log_line_containing` to scripts/run.py, used by `relaunch` to append `: <line>` to the two error messages. The MCP `relaunch` tool already joins on_error messages into its ToolError, so add a test in tests/test_mcp_server.py confirming it carries the line.
3. Update docs/development.md, run `task check`, commit.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
`run.relaunch` now appends the full matching log line to the load-failed and unsupported-map errors (`relaunch: the level failed to load: <line>`). The line comes from the new `log_line_containing`, which takes the first match after the last `DevHarness: enabled`. With no match the error keeps the old fixed hint, and the success and timeout paths are untouched. The MCP `relaunch` tool already joins on_error messages into its ToolError, so it carries the same text. Verified with `task check` (274 tests passing, including 7 new ones and an MCP error test). Not exercised against the live game.
<!-- SECTION:FINAL_SUMMARY:END -->
