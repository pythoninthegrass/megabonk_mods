---
id: TASK-032.04
title: Validation and kill floor for from-scratch levels without baseline assumptions
status: Done
assignee: []
created_date: '2026-11-04 20:37'
updated_date: '2026-11-04 22:48'
labels: []
dependencies:
  - TASK-032.02
  - TASK-032.03
parent_task_id: TASK-032
priority: high
ordinal: 157000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Parent TASK-032. Reachability validation and the kill floor must work for a from-scratch level without relying on generated objects or a generated grid.

Today the editor's Validate finds its start cell by searching generated objects whose name contains "spawn" and "portal" (EditorTileTools.SpawnCell in src/MegabonkLevels.Mod/editor_tile_tools.cs) and the boss cell from the generated boss portal (LiveEditPatch.BossPortalCell). The kill floor (kill_floor.cs) derives from the lowest live tile level, or an authored killFloorY, clamped above the game's catch floor. BossSpawnRedirectPatch needs real ground under the boss spawner.

For from-scratch levels the start and boss cells come from the authored spawn and bossSpawner. Extract a pure, tested function that picks validation targets from the level file and level state, and keep the existing name search for generated-baseline levels. Write tests first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Validate on a from-scratch level starts from the authored spawn cell and checks the authored boss spawner cell, with no name search of generated objects
- [x] #2 Validate on a generated-baseline level behaves exactly as before
- [x] #3 Validation warns when the boss spawner sits over an empty cell and no placed mesh provides ground
- [x] #4 The kill floor arms for a from-scratch level from its authored grid, or from killFloorY when set, and stays clamped above the catch floor; a unit test covers a grid-derived state
- [x] #5 The target-selection logic is a pure function with tests written first
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first: ValidationTargets.Select(LevelFile, LevelState) pure function (from-scratch: start/boss cells from authored spawn/bossSpawner, no name search; generated baseline: signals name search; warning when boss cell has no tile and no placed object in LevelState.Objects sits in that cell - option A, cannot tell ground from decoration).
2. Tests first: KillFloor.FloorYForGrid derives from an authored grid's lowest height via FloorY, clamped above the catch floor; killFloorY still wins via FloorYExplicit.
3. Wire EditorTileTools.Validate to the selector (generated baseline keeps SpawnCell/BossPortalCell) and KillFloorWatcher.Arm for from-scratch levels; confirm KillFloor: armed in the log on a from-scratch load.
4. Update docs/development.md, run task check, conventional commit with no attribution.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added ValidationTargetSelector (validation_targets.cs), a pure function choosing Validate's start and boss cells: from-scratch levels use the authored spawn and bossSpawner cells with no name search; generated-baseline levels return a NameSearch marker and keep SpawnCell/BossPortalCell unchanged. It warns when the boss cell has no tile and no placed object in LevelState.Objects sits in it; any placed object counts as ground, since a catalog id does not say whether a mesh can be stood on. EditorTileTools.Validate uses it via FromScratchGenerationPatch.ActiveLevel and appends the warning to the summary line.

Kill floor needed no production change: the from-scratch build creates the live tiles from the authored grid, so KillFloorWatcher.Arm already derives from the authored grid, honours killFloorY and clamps above the catch floor. Verified in game on levels/from-scratch-fixture.mblevel.json ("KillFloor: armed at y=-12 (derived from tiles, catch floor y=-20)"). Added unit tests deriving the floor from a LevelGrid state.

Limit: the editor status second line is clipped in the toolbar, so the Validate summary text was not read in game; Validate ran without errors in the log. Logic is covered by unit tests.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
