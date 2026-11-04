---
id: TASK-032.04
title: Validation and kill floor for from-scratch levels without baseline assumptions
status: To Do
assignee: []
created_date: '2026-11-04 20:37'
updated_date: '2026-11-04 20:37'
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
- [ ] #1 Validate on a from-scratch level starts from the authored spawn cell and checks the authored boss spawner cell, with no name search of generated objects
- [ ] #2 Validate on a generated-baseline level behaves exactly as before
- [ ] #3 Validation warns when the boss spawner sits over an empty cell and no placed mesh provides ground
- [ ] #4 The kill floor arms for a from-scratch level from its authored grid, or from killFloorY when set, and stays clamped above the catch floor; a unit test covers a grid-derived state
- [ ] #5 The target-selection logic is a pure function with tests written first
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
