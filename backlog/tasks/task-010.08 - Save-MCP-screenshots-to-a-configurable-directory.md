---
id: TASK-010.08
title: Save MCP screenshots to a configurable directory
status: Done
assignee:
  - Assistant
created_date: '2026-10-25T18:11:00Z'
updated_date: '2026-10-25T18:18:00Z'
labels:
  - dev-harness
  - tooling
dependencies: []
references:
  - scripts/mcp_server.py
  - scripts/run.py
  - tests/test_mcp_server.py
documentation:
  - docs/development.md
modified_files:
  - scripts/mcp_server.py
  - tests/test_mcp_server.py
  - docs/development.md
parent_task_id: TASK-010
priority: medium
type: enhancement
ordinal: 66000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The megabonk MCP screenshot tool returns images inline but offers no way to retain a named evidence file. During removed-tile wall verification, saving screenshots required falling back to `uv run scripts/run.py screenshot .tools/removed-tile-checks/final-editor-slope.png`. Agents should be able to capture, inspect, and retain verification evidence in one MCP call without dropping to the script. The requested default destination is the MCP server working directory, with a keyword argument for a custom directory; named files should also be supported.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Calling screenshot() without arguments saves a PNG in the MCP server working directory with a unique timestamped filename.
- [x] #2 screenshot accepts an optional directory keyword argument; relative directories resolve against the MCP server working directory and absolute directories are supported.
- [x] #3 screenshot accepts an optional filename keyword argument for a named evidence capture in the chosen directory.
- [x] #4 A successful screenshot call still returns the image inline and also reports the saved absolute file path.
- [x] #5 Existing files are never silently overwritten; destination or filename errors return actionable tool errors without modifying existing files.
- [x] #6 Automated tests cover default/custom destinations, relative/absolute paths, filename selection, collision handling, error reporting, and inline image plus path results.
- [x] #7 docs/development.md documents the default destination, keyword arguments, directory-creation behavior, overwrite policy, and examples; an end-to-end game check confirms inline display and a readable saved PNG through MCP only.
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
1. Add in-memory MCP tests first for default timestamped captures, relative/absolute directories, named files, validation, collisions including races, filesystem/harness errors, and mixed image/path results.
2. Extend screenshot with optional directory/filename keywords. Create missing parent directories, validate PNG basenames, capture to an isolated temporary file in the destination directory, then publish via an exclusive hard link so existing files/symlinks cannot be overwritten. Return inline Image plus saved absolute path and actionable ToolError on filesystem failures.
3. Document arguments, directory creation, overwrite/error policy and examples in docs/development.md.
4. Run targeted tests and task check; start a fresh MCP process against the live game to verify inline image and readable retained PNG using MCP only. Record evidence and complete with a conventional commit scoped to this task.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Tests added before implementation: initial red run exposed missing destination/path behavior; targeted suite then passed (53 MCP tests). Full task check passed with 679 C# tests, 185 Python tests, markdownlint and ruff; existing nullable C# warnings remain.

Live verification used MCP only for game operations: initial state/screenshot timed out because the game was not responding; megabonk.relaunch restored a frozen invulnerable editor session. A fresh stdio MCP client captured .tools/screenshot-evidence/editor-retained-010-08.png (1512x982, 2,025,138 bytes), verified inline image/png bytes exactly matched saved file, confirmed a repeat named capture failed without changing the file, and confirmed default timestamped capture landed in server cwd. Read the retained PNG successfully and inspected the editor overlay. Removed only the temporary default live-check PNG; named evidence remains gitignored.

Atomic publication uses same-filesystem hard links; unsupported filesystems return actionable errors. Restart existing MCP server connections to expose the new directory/filename arguments.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Implemented screenshot(directory=None, filename=None) with timestamped cwd defaults, automatic directory creation, validated PNG basenames and inline image plus saved absolute path. Staged capture and atomic hard-link publication protect existing files and symlinks, including races; failures provide actionable tool errors. Added tests first and retention documentation. Verification: task check passed (679 C# tests, 185 Python tests, lint), plus live MCP default/named captures, byte-for-byte inline/saved comparison and collision protection. Evidence: .tools/screenshot-evidence/editor-retained-010-08.png. Implementation committed as 21c6eac. Restart MCP connections to discover updated arguments; destination filesystem must support hard links.
<!-- SECTION:FINAL_SUMMARY:END -->
