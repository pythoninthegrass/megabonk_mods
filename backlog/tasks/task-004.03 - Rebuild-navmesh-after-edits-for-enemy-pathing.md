---
id: TASK-004.03
title: 'Support slope and added-tile edits live, and rebuild navigation after edits'
status: To Do
assignee: []
created_date: '2026-10-06 21:42'
updated_date: '2026-10-08 02:14'
labels:
  - level-editor
dependencies:
  - TASK-004.02
parent_task_id: TASK-004
priority: high
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-004 first for full context.

## Part 1: slope and added-tile edits (carried over from TASK-004.02)

TASK-004.02 applies tile height edits and tile removal to the live map, but two op types are not applied yet and only log a warning: SetTileSlope to a non-None direction, and AddTile on a cell that has no live tile. Both are needed before TASK-004.05's test level (which exercises all six edit op types) can pass. Read docs/level-format.md ("Applying edits to the live game") and docs/runtime-map-structure.md first; live_edit_patch.cs (LiveEditPatch.Applier) is where they plug in.

Known context from TASK-004.02: the live tile grid (ProceduralTileGeneration.proceduralTiles) is a dense size x size array for Tiles maps, so AddTile only has an effect where a cell is empty (for example after RemoveTile nulled it, or beyond the grid, which is out of scope). Slope tiles are separate prefabs (TileSlope vs TileGround, with rotation), not a property of a ground tile, so a slope edit means replacing the tile with the right prefab and orientation. A height change moves only the tile itself, so wall and fill pieces around it (flatTiles/fillTiles) are not adjusted; decide whether these edits must also keep neighbouring wall and fill pieces consistent, and document the outcome.

## Part 2: navigation after edits

Using TASK-002.03's confirmed findings on whether/how Megabonk bakes a NavMeshSurface (or whatever pathing mechanism it actually uses), make sure enemies can path onto tiles that were added, moved, or had height/slope changes after TASK-004.02's edits are applied, and do NOT path onto tiles that were removed.

TASK-002.03 found that the open Tiles and ProceduralMesh maps (Forest, Desert) bake no navmesh at all, and enemy movement (EnemyMovementRb) is direct Rigidbody-based chase toward the player. The only NavMeshSurface bake is the Graveyard crypt/boss dungeon (RsgController.navmeshSurface.BuildNavMesh()). So for the open maps this part may reduce to confirming that enemies physically traverse edited terrain, and for removed tiles, keeping them off holes. If the mechanism turns out to be substantially harder than expected, flag the risk to Lance rather than shipping a level editor where enemies get stuck on edited terrain.

Verify with a real playthrough: edit a level to add a new path, or let enemies naturally path toward the player across an edited tile, and confirm no enemies become stuck.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Navigation data is rebuilt/rebaked after edits are applied, using whatever mechanism TASK-002.03 confirmed the game actually uses
- [ ] #2 Enemies successfully path onto added or height/slope-modified tiles in a real playthrough
- [ ] #3 Enemies do not attempt to path onto removed tiles
- [ ] #4 If the confirmed mechanism differs substantially from a simple NavMeshSurface rebuild, the actual approach is documented and any added risk/complexity is flagged
- [ ] #5 SetTileSlope to a non-None direction from a loaded level file is applied to the live map and visibly changes the tile (correct prefab and orientation)
- [ ] #6 AddTile on a cell with no live tile instantiates a tile at the correct world position, with spacing read from StageData.mapParameters at runtime
- [ ] #7 Wall and fill pieces next to height, slope, added, or removed tiles are handled consistently, or the remaining visual gap is documented as a known limit
- [ ] #8 Pure logic introduced for slope and added-tile handling is unit tested, with the tests written before the implementation
<!-- AC:END -->



## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
