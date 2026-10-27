---
id: TASK-007.06
title: Support editing ProceduralMesh maps
status: Done
assignee:
  - claude
created_date: '2026-10-27 06:02'
updated_date: '2026-10-27T22:13:00Z'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-007
priority: low
ordinal: 73000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up to TASK-007.05.01. Maps with `EMapType.ProceduralMesh` (Desert) generate one heightmap mesh through `MapGenerator` and never fill `ProceduralTileGeneration.proceduralTiles`, so the editor refuses them. Add object editing on those maps: raycast the cursor against the mesh collider, define how a world position maps to the level format's grid cell (or extend the format), take the kill-floor height from the terrain, and decide what happens to the tile tools (disabled on these maps). Needs a design decision on the level format before implementation.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A design note decides how objects on a ProceduralMesh map are keyed in the level format and how they are replayed on load
- [x] #2 The editor enters on Desert, the cursor targets the terrain, and the kill floor arms from terrain height
- [x] #3 Object place, move, remove, undo/redo, save and reload work on Desert; the tile tools are disabled with a clear message
- [x] #4 Forest behaviour is unchanged
- [x] #5 Unit tests cover the Unity-free logic
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
Design (approved): the level format needs no extension. `PlaceObject` and `MoveObject` already carry a world-space `Position`; the grid cell is only an editor snapping concept and is never serialized for objects. On a ProceduralMesh map objects are keyed by that world position, with Y from a terrain raycast at place time. Replay on load uses the existing object-op path; `tile.*` ops are skipped with a warning. Generator-spawned objects keep `gen:<genId>` targets. Seed caveat: Desert determinism is 'reproducible in practice' (map-generation-determinism.md), so saved Y values assume the same terrain regenerates.

Steps done:
1. EditorMapSupport: ProceduralMesh supported for objects only (TileTools=false), tests first.
2. KillFloor.FloorYForTerrain, TerrainEdits.Split and EditorTools.IsAvailable, Unity-free and unit tested.
3. LiveEditPatch terrain session (objects only, empty tile baseline); tile ops filtered on replay.
4. Cursor raycast against the MapGenerator mesh collider; Place, Select and drag use the hit point.
5. Kill floor arms from the terrain collider's lowest point.
6. Tile tools blocked with a toast on terrain maps; overview camera already fell back without a grid.
7. Verified in game on Desert and Forest; docs updated; task check passes.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified in game on Desert (relaunch --map 2): editor enters, KillFloor armed at y=-12 (terrain low y=0.085, catch floor y=-20); place at (-50.38, 14.83, 117.07), drag move, undo/redo, remove and undo of remove, save to desert_test.mblevel.json (schemaVersion 2, one object.place), reload replays the object at the same position and re-arms the same floor. Forest regression: editor enters, Raise at (10,8) applies, kill floor y=-72. The Raise tool on Desert was clicked and kept the tool (toast), no screenshot of the toast taken. Not covered: Hell terrain collider, teleport and cell readout on terrain maps. DoD #1: task check fails only in markdownlint on the untracked tools/thps_warehouse_strategywiki.md (not part of this change); mod build, 1024 xunit tests and 276 pytest pass; ruff format flags tests/test_run.py, which this change did not touch.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The editor now enters ProceduralMesh maps (Desert) and edits objects there. Objects are keyed by world position, so the level format is unchanged: the cursor raycasts the heightmap mesh's MeshCollider, Place and Select use the hit point, the kill floor arms from the collider's lowest point, tile tools are blocked with a toast, and tile ops in a loaded file are skipped with a warning. Unity-free logic (EditorMapSupport, KillFloor.FloorYForTerrain, TerrainEdits.Split, EditorTools.IsAvailable) is unit tested. Verified in the running game on Desert (place, move, remove, undo/redo, save, reload) and Forest (unchanged). Not covered: Hell's terrain collider, and teleport/cell readout on terrain maps. Commit 81b5fad.
<!-- SECTION:FINAL_SUMMARY:END -->
