---
id: TASK-018.03
title: Save and list custom levels through harness commands
status: Done
assignee:
  - claude
created_date: '2026-10-27T07:23:00Z'
updated_date: '2026-10-27T17:12:00Z'
labels:
  - dev-harness
  - tooling
dependencies: []
references:
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
documentation:
  - docs/development.md
parent_task_id: TASK-018
priority: medium
type: enhancement
ordinal: 78000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The editor's Save is reached via an injected click, and reloading a saved level needs a hand-written harness command file whose path must be known. Add harness commands `save_level(level?)` (invokes the editor save, optionally naming the target level) and `list_levels` (returns the saved custom-level files). This makes the save/reload loop verifiable via typed commands instead of clicks + disk reads, and removes the need to know the save path. Mod-side; verify in the real game.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `save_level` saves the current editor level, optionally to a named level file, and returns the result.
- [x] #2 `list_levels` returns the saved custom-level files.
- [x] #3 Verified in the real game: edit, save_level, list_levels shows the file, reload it.
- [x] #4 docs/development.md documents the commands; task check passes.
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
1. Parse `save-level` (optional `level`) and `list-levels` in harness_command.cs, tests first.
2. EditorTileTools.SaveLevel reuses Save(), setting the save field from `level`; DevHarness.ListLevels wraps LiveEditPatch.ListLevelFiles.
3. run.py verbs and MCP tools save_level and list_levels.
4. Document in docs/development.md; verify in the game.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `save-level` (optional `level`; returns name, path, edit count; fails outside editor mode or on a write error) and `list-levels` (returns directory and sorted file names) harness commands, with `run.py` verbs and `save_level`/`list_levels` MCP tools. Verified in the CrossOver game: raised a tile (count 1), `save-level harness_check` wrote the file, `list-levels` showed it, `state` reported saved and clean, and a fresh run reloaded it through the Load widget with count 1. `save-level` with the editor off was rejected with `editor mode is off`. `task check` passes (969 C# tests, 206 Python tests). The running MCP server must be restarted to expose the new tools; `relaunch(level)` does not accept a Windows-style path.
<!-- SECTION:FINAL_SUMMARY:END -->
