---
id: TASK-032.05
title: 'Editor: create a new from-scratch level and save its full state'
status: Done
assignee: []
created_date: '2026-11-04 20:37'
updated_date: '2026-11-05 01:15'
labels: []
dependencies:
  - TASK-032.02
  - TASK-032.03
  - TASK-032.04
parent_task_id: TASK-032
priority: high
ordinal: 158000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Parent TASK-032. The editor can only edit on top of a generated map today: entering is refused unless a run is in progress, and Save writes only the edit list (EditorTileTools.Save in src/MegabonkLevels.Mod/editor_tile_tools.cs, LiveEditPatch.SnapshotLevelFile). It needs a way to start a blank from-scratch level and to save one.

New level: a command taking map, stage and grid size writes a minimal from-scratch file (a flat grid with the spawn and boss spawner on it) and loads it through the normal relaunch and load path; it does not mutate the live map. Expose it as an editor button, a dev harness verb, a run.py command and an MCP tool, following how the existing harness verbs are wired (harness_command.cs, dev_harness.cs, scripts/run.py, scripts/mcp_server.py).

Save for a from-scratch session writes the current tile state into the grid, folds object moves and removes into final placements, and writes spawn and bossSpawner from the player-start and boss-destination markers. The fold is a pure, tested function. The editor's load guard compares map, stage and tier and ignores the seed for from-scratch files. Write tests first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The editor button, harness verb, run.py command and MCP tool each create a blank from-scratch level and open it in the editor
- [x] #2 A new level can be edited with the tile and object tools, saved, reloaded and shows the same grid and placements
- [x] #3 A saved from-scratch file contains a grid, spawn and bossSpawner and no tile edit ops or gen: targets
- [x] #4 Moving then removing a placed object saves as no placement; moving it saves one placement at the final position; covered by unit tests
- [x] #5 Loading a from-scratch level inside the editor is not refused over a seed mismatch
- [x] #6 Python tests cover the run.py and MCP wiring, in the style of the existing tests
- [x] #7 docs/development.md documents the new-level workflow
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first: pure fold (LevelState + settings markers -> Grid, Spawn, BossSpawner, final object.place edits); move-then-remove folds to nothing, move folds to one placement at the final position; no tile.* ops or gen: targets.
2. Tests first: pure blank-level builder (map, stage, grid size -> minimal from-scratch LevelFile: flat grid, spawn at centre, boss spawner two cells east), validated by LevelFileValidation, refused above the stage's stock size via FromScratchLayout.SizeRefusal. Defaults: Forest, stage 0, tier 0, 7x7.
3. Save: EditorTileTools.Save uses the fold when FromScratchGenerationPatch.ActiveLevel is set; generated-baseline saves unchanged.
4. new-level on four surfaces following save-level: harness verb (harness_command.cs, dev_harness.cs), editor button, run.py command, MCP tool; writes the file to UserData/Levels and loads it through the normal load path. Python tests in the style of test_run.py and test_mcp_server.py.
5. Find where the editor load compares map/stage/tier/seed and ignore the seed for from-scratch files.
6. In-game check (create, edit tiles and objects, save, reload, compare), docs/development.md new-level workflow, task check, conventional commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
In game: run.py new-level and the editor New button each wrote a level, built it and re-entered the editor; the MCP new_level tool is covered by the payload test only, because the running MCP server has to be restarted to see a new tool. Edited a 5x5 level (one raised tile, one placed tree), saved, reloaded through the editor Load and re-saved: the two files were identical apart from gameBuildId.

Interpretation: the editor's Load of a from-scratch file starts a fresh run (EditorLoadPlan) instead of swapping in place, so a seed mismatch can never refuse it. The 'player-start and boss-destination markers' are the playerStart and bossSpawnPosition settings; both are folded into spawn and bossSpawner and omitted from the saved file.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added BlankLevel (blank from-scratch file builder), FromScratchSnapshot (pure fold of tiles, object edits and markers into the saved file), EditorLoadPlan (in place, fresh run or refuse) and EditorFileNaming.NewLevelFileName, all tested first. new-level is wired on the editor toolbar (New button), the harness (new-level verb, NewLevelArgs), run.py (new-level) and the MCP server (new_level). EditorTileTools.Save folds a from-scratch session through LiveEditPatch.FoldFromScratch after the settings panel is applied; the editor Load uses EditorLoadPlan. Docs: docs/development.md harness table, result lists, MCP tool list and a new 'Creating and saving a from-scratch level' section.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
