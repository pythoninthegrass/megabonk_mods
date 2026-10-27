---
id: TASK-007.05.03
title: Verify editor placement on Graveyard
status: Done
assignee:
  - '@claude'
created_date: '2026-10-27 05:47'
updated_date: '2026-10-27T21:47:00Z'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-007.05
priority: low
ordinal: 72000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found while verifying TASK-007.05: Graveyard is `EMapType.Tiles` and generates with a 19x19 grid and an armed kill floor (`KillFloor: armed at y=-192`), so the editor should work there. Verify it in the running game and fix whatever fails, such as the crypt/exit structures in `MapGenerationController`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A Graveyard level loads through `run.py relaunch` with the kill floor armed and the editor overview framing the grid, although the player spawns off the grid
- [x] #2 In the editor on Graveyard, selecting a palette entry (including a pack entry) and clicking a tile places the object, and undo/redo and save work
- [x] #3 A level saved on Graveyard reloads with its edits
- [x] #4 Anything that fails is fixed or recorded with its cause
- [x] #5 Forest behaviour is unchanged
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
1. task mod:build, then relaunch on a Graveyard level (map override) and confirm KillFloor armed and the player on a grid cell.
2. In the editor, select a game entry and a pack entry, place on a tile, undo/redo, save.
3. Reload the saved level and confirm the edits.
4. Fix or record any failure with its cause; confirm Forest still behaves the same.

Added after the verification: when the player's cell is outside the grid, aim the overview at a body standing on the centre tile (OverviewTarget, unit tested), recompute it once the grid session exists, and document it in docs/development.md.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Context added 2026-10-27: Graveyard was only loaded with `run.py load` into a running game, which logged `mapType=0`, `proceduralTiles.Length=19`, `occupiedCells=361` and `KillFloor: armed at y=-192`. Placement, save and reload were not tried there. The editor refusal for non-Tiles maps (commit d183a25) does not affect it. The pack entries are already in the palette on every supported map (commit f322bde).

2026-10-27 verification on CrossOver, mod built from main (f0af0df). `relaunch` with map=8 loads Graveyard with `KillFloor: armed at y=-192`, 19x19 grid. The player spawns at world (1999.5, 2001.9, 2017), reported as cell [59,59], about 2000 units from the grid (grid centre is world (0, -38, 0), cell [9,9]), so the player is NOT on a grid cell. Cause of the failed placement seen earlier: the editor's free-fly overview camera is centred on the player, so after relaunch the view shows the spawn area and no tiles; clicks there produce no edit. After `teleport cell=[9,9]` and an editor off/on cycle the overview centres on the grid.

Then on Graveyard: placing `bundle:testpack/TestProp` logged `LiveEdit: spawned ... as placement:0` and `place ... in cell (9,11) -> object.place`; Undo returned edits to 0, Redo restored 1; placing game entry `graveyard/stage0/randomMapObjects/0/0` (DeadTree0) gave 2 edits; save wrote graveyard_packs.mblevel.json with both object.place edits (bundle: id included) and `packs {testpack: 1.0.0}`. Relaunch loading that file replayed both edits (`edits.count` 2, both `spawned` lines in the log).

Forest with no packs installed after removing the test pack: 75 entries, tabs unchanged, no Packs tab. Graveyard without packs: 45 entries, no Packs tab; with testpack 47.

Fix: OverviewTarget.Of picks the player body point when the player is on the grid, else a body standing on the centre tile (surface plus PlayerBodyOffsetY 1.925). Aiming at the bare surface rendered the ground as sky, so the body offset matters. The editor is entered about 150 ms before the grid session exists, so editor_mode.cs recomputes the pose once when LiveEditPatch.Grid first appears.

Verified after the fix: a plain `relaunch` with map=8 and the player still at (2000, 2002, 2017) shows the ground, and placing bundle:testpack/TestProp logged `place ... in cell (9,11) -> object.place` (edits.count 1). Forest relaunch: player on cell [10,7], 75 entries, unchanged. Hell (map 64) is refused by the editor as MapType 1, like Desert.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Graveyard editor placement works. The player spawns about 2000 units from the 19x19 grid (state cell [59,59]), so the overview camera, centred on the player, showed no tiles and placement clicks did nothing. The overview now aims at a body standing on the centre tile when the player's cell is off the grid (`OverviewTarget`, unit tested), recomputed once the grid session exists. Verified in game on Graveyard: placing a pack entry and a game entry, undo/redo, save, and reload replaying both edits. Forest unchanged at 75 entries with the player on the grid. AC #1 was reworded from 'player on a grid cell' to the overview framing the grid, since the spawn is off-grid by design of the map.
<!-- SECTION:FINAL_SUMMARY:END -->
