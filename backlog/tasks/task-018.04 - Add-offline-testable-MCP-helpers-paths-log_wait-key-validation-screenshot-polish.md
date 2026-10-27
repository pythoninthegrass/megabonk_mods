---
id: TASK-018.04
title: >-
  Add offline-testable MCP helpers: paths, log_wait, key validation, screenshot
  polish
status: To Do
assignee: []
created_date: '2026-10-27T07:23:00Z'
labels:
  - dev-harness
  - tooling
dependencies: []
references:
  - scripts/mcp_server.py
  - tests/test_mcp_server.py
documentation:
  - docs/development.md
parent_task_id: TASK-018
priority: medium
type: enhancement
ordinal: 75000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
These four additions live entirely in scripts/mcp_server.py and are fully testable against the fake-mod harness in tests/test_mcp_server.py without starting the game — do these first. Command names use snake_case.

- `paths()` returns the game directory, harness folder, latest log path and the custom-level save directory. Currently an agent must hand-type the long Wine prefix path to write harness command files directly (as in TASK-016 AC#4's reload step) or shell out to game_paths.py.
- `log_wait(pattern, timeout)` blocks until Latest.log has a line matching pattern, then returns it, or raises on timeout. `load` returns as soon as the command is accepted, before the level is armed, and there is no current synchronous wait, so agents sleep.
- `key(name)` raises a tool error for a key name the mod does not accept, instead of the mod silently ignoring it. The valid names live in the mod's key_names.
- `screenshot` polish: default the capture to a gitignored directory so it never clutters the repo working tree, add an overwrite flag and an optional scale/crop to cut token cost (it already supports directory/filename).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 `paths()` returns the game directory, harness folder, latest log path and the custom-level save directory.
- [ ] #2 `log_wait(pattern, timeout)` returns once a matching log line appears and raises a tool error on timeout.
- [ ] #3 `key` raises a tool error for a key name the mod does not accept, instead of silently no-oping.
- [ ] #4 `screenshot` defaults to a gitignored directory, supports overwrite and an optional scale/crop, and never clutters the repo working tree.
- [ ] #5 Each tool has a fake-mod test in tests/test_mcp_server.py (no game needed), task check passes, and docs/development.md documents the new tools.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
