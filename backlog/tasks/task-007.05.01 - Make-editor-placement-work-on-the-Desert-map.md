---
id: TASK-007.05.01
title: Refuse editor mode on ProceduralMesh maps (Desert)
status: Done
assignee:
  - '@claude'
created_date: '2026-10-27 05:47'
updated_date: '2026-10-27 06:07'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-007.05
priority: low
ordinal: 70000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found while verifying TASK-007.05: in the editor on Desert, placing an object does nothing. Desert is `EMapType.ProceduralMesh`, built by `MapGenerator` as one heightmap mesh, so `ProceduralTileGeneration.proceduralTiles` and `currentMapParameters` stay null (`GridShape: proceduralTiles is null`). The editor's tile tools, live-edit replay, kill floor, collision rebuild and the cell-keyed level format all depend on that grid. Supporting mesh maps is a separate, larger task. Here, the editor refuses clearly on a ProceduralMesh map instead of entering a state where nothing works, and `relaunch` fails fast with the reason.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The cause of the unresolved `proceduralTiles` / `MapParameters` on Desert is identified and documented
- [x] #2 A Unity-free support check maps `EMapType` to supported (Tiles) or unsupported with a reason (ProceduralMesh), unit tested first
- [x] #3 On a ProceduralMesh map the editor does not enter: a log warning names the reason, and the harness `editor on` result is rejected with it (no toast: the toast UI belongs to the editor overlay, which is not built when entry is refused)
- [x] #4 `run.py relaunch` into a Desert level fails fast with that reason instead of retrying until timeout
- [x] #5 Verified in the running game: Desert refuses cleanly and Forest still enters the editor and places objects
- [x] #6 docs/development.md states that the editor needs a Tiles map and that ProceduralMesh maps such as Desert are refused
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Failing test first: Unity-free `EditorMapSupport.For(EMapType)` returns supported for Tiles and unsupported-with-reason for ProceduralMesh.
2. Implement it; call it where editor mode is entered (toast, log warning, harness `editor on` reports the reason, editor stays off).
3. Make `relaunch` stop retrying and report the reason when the harness says the map is unsupported.
4. Docs: docs/development.md limitation.
5. Verify in game: Desert refuses, Forest enters and places. task check.
6. Conventional commit, no attribution.

Done: toast dropped (see notes); Forest regression checked in game after the change (editor entered, palette 77 entries, TestModel placed at cell (10,7)).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Root cause (AC #1): the game logs `mapType=1` for Desert, which is `EMapType.ProceduralMesh` (Forest is `EMapType.Tiles`). A ProceduralMesh map is built by `MapGenerationController.proceduralMapMeshGenerator` (`MapGenerator`: noise heightmap, `terrainData`, one mesh) and never fills `ProceduralTileGeneration.proceduralTiles` or `currentMapParameters`, so `GridShapePatch` correctly reports null.

Everything the editor needs from the grid reads `proceduralTiles`: `kill_floor_watcher.cs` (Arm, LiveLevels), `live_edit_patch.cs` (SnapshotGrid, replay, tile ops), `fill_regeneration.cs`, `collision_rebuild.cs`, and the cell-keyed level format (placeObject carries a grid cell). So this is a design gap, not a bug in `grid_shape_patch.cs`; see the open question to the user.

2026-10-27: tests first (editor_map_support_tests.cs; test_run.py relaunch fail-fast and wait_for_any_log_line) failed, then EditorMapSupport, EditorMode.CurrentMapSupport (Enter refuses, GenerationPatch warns after generation), harness `editor on` rejects with the reason, and run.py relaunch waits for either `KillFloor: armed` or `EditorMode: unsupported map`. In game: relaunch into Desert stops in about 14 s with the reason and exit 1; `editor on` prints 'MapDesert is not a tile map (mapType=1); the editor needs a tile grid.' and is rejected. The planned toast was dropped: it renders only in the editor overlay, which is not built on refusal, and a queued toast would show stale on the next entry. AC #3 amended to match.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The editor refuses to enter on maps that are not `EMapType.Tiles`. Desert is `ProceduralMesh`, one heightmap mesh that never fills `ProceduralTileGeneration.proceduralTiles`, which the tile tools, live edit, kill floor and the cell-keyed level format depend on. `EditorMapSupport.Check` (Unity-free, unit tested) decides; `EditorMode.Enter` and the harness `editor on` command refuse with the reason, `GenerationPatch` warns after generation, and `run.py relaunch` stops on `EditorMode: unsupported map` instead of retrying until timeout. No toast: it renders only in the editor overlay. Support for mesh maps is TASK-007.06. Commit d183a25.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
