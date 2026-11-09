---
id: TASK-018.04
title: >-
  Add offline-testable MCP helpers: paths, log_wait, key validation, screenshot
  polish
status: Done
assignee:
  - claude
created_date: '2026-10-27T07:23:00Z'
updated_date: '2026-10-27T17:20:00Z'
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
- [x] #1 `paths()` returns the game directory, harness folder, latest log path and the custom-level save directory.
- [x] #2 `log_wait(pattern, timeout)` returns once a matching log line appears and raises a tool error on timeout.
- [x] #3 `key` raises a tool error for a key name the mod does not accept, instead of silently no-oping.
- [x] #4 `screenshot` defaults to a gitignored directory, supports overwrite and an optional scale/crop, and never clutters the repo working tree.
- [x] #5 Each tool has a fake-mod test in tests/test_mcp_server.py (no game needed), task check passes, and docs/development.md documents the new tools.
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
1. paths(): return game_dir, harness, latest_log, levels_dir (game_dir/UserData/Levels, mirrors LiveEditPatch.LevelsDirectoryPath). No game needed.
2. log_wait(pattern, timeout=30, since_launch=True): poll Latest.log off the event loop, return first matching line, ToolError on timeout or bad regex.
3. key: validate name and modifiers client-side against a Python mirror of KeyNames.All (the mod already rejects unknown names, so this saves a round trip and gives a listed-names error); a test asserts the mirror matches src/MegabonkLevels.Mod/key_names.cs.
4. screenshot: default directory = repo .tools/evidence (gitignored) instead of server cwd; overwrite flag; optional scale (0-1] and crop [x,y,w,h] applied to the inline image via Pillow (full-res capture is what gets saved). Add pillow to the script deps and the scripts:test --with list.
5. Tests first in tests/test_mcp_server.py for each; update existing screenshot tests for the new default. Update docs/development.md MCP section.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added paths(), log_wait(pattern, timeout, since_launch), client-side key/modifier name validation (Python mirror of key_names.cs, with a parity test), and screenshot overwrite/scale/crop with a default of the gitignored .tools/evidence. Scale and crop shrink only the inline image; the saved file is the full capture. Pillow added to the script deps and the scripts:test command. 226 Python tests pass and task check passes; docs/development.md updated. Not exercised against the live game.
<!-- SECTION:FINAL_SUMMARY:END -->
