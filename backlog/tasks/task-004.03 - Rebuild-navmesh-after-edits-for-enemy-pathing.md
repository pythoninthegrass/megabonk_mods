---
id: TASK-004.03
title: 'Support slope and added-tile edits live, and rebuild navigation after edits'
status: In Progress
assignee:
  - Claude
created_date: '2026-10-06 21:42'
updated_date: '2026-10-08 03:45'
labels:
  - level-editor
dependencies:
  - TASK-004.02
  - TASK-004.08
  - TASK-004.09
modified_files:
  - src/MegabonkLevels.Mod/live_edit_patch.cs
  - src/MegabonkLevels.Mod/tile_placement.cs
  - src/MegabonkLevels.Mod/reachability_validator.cs
  - tests/MegabonkLevels.Tests/tile_placement_tests.cs
  - tests/MegabonkLevels.Tests/reachability_validator_tests.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - docs/level-format.md
  - docs/runtime-map-structure.md
  - docs/development.md
  - scripts/run.py
  - scripts/test_run.py
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
- [x] #1 Navigation data is rebuilt/rebaked after edits are applied, using whatever mechanism TASK-002.03 confirmed the game actually uses
- [ ] #2 Enemies successfully path onto added or height/slope-modified tiles in a real playthrough
- [ ] #3 Enemies do not attempt to path onto removed tiles
- [x] #4 If the confirmed mechanism differs substantially from a simple NavMeshSurface rebuild, the actual approach is documented and any added risk/complexity is flagged
- [ ] #5 SetTileSlope to a non-None direction from a loaded level file is applied to the live map and visibly changes the tile (correct prefab and orientation)
- [x] #6 AddTile on a cell with no live tile instantiates a tile at the correct world position, with spacing read from StageData.mapParameters at runtime
- [x] #7 Wall and fill pieces next to height, slope, added, or removed tiles are handled consistently, or the remaining visual gap is documented as a known limit
- [x] #8 Pure logic introduced for slope and added-tile handling is unit tested, with the tests written before the implementation
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved by Lance. Steps 1-5 are done; step 6 is open and blocked on TASK-004.08 (freeze) and TASK-004.09 (camera pose).

1. [done] Observed 40 live Forest slope tiles on macOS/CrossOver: a slope tile is the `slopeTile` prefab at `posY` p, `ProceduralTile.dir` points uphill and the yaw follows it (dir +Z = 0, +X = 90, -Z = 180, -X = 270), and the uphill neighbour is always at p + 1.
2. [done] Wrote failing tests first (tile_placement_tests.cs): slope direction to grid step and back, move/replace/add decision from live occupancy and target TileState, world position from scaledTileWidth/scaledTileHeight. New file tile_placement.cs, registered in the test csproj.
3. [done] Implemented in live_edit_patch.cs: a SetTile that changes tile kind, or lands on an empty cell, instantiates `slopeTile` or `flatTile` through the game's `InstantiateTile(cell, height, prefab, dir, parentDir)`, destroys the old tile, and updates `proceduralTiles[x][z]` and `tiles`. A same-kind SetTile still only moves the tile. AddTile outside the grid logs a warning (out of scope).
4. [done] Reworked ReachabilityValidator to the observed model (SlopeDirection is the uphill side, a slope spans h to h + 1, side edges connect to nothing, tiles connect when facing edge heights match), with its tests rewritten first. This replaced the earlier downhill-on-the-higher-tile assumption.
5. [done] Wall and fill pieces next to edited tiles are not regenerated; documented as a known limit in docs/level-format.md (FillHoles/FillEdges are private whole-grid passes that would duplicate pieces and shift genIds). Navigation: open maps bake no navmesh and enemies use Rigidbody chase, so no rebuild is needed; AC #1 closed as not applicable and documented in docs/runtime-map-structure.md under AC #4.
6. [open] Visual and playthrough verification once TASK-004.08 and TASK-004.09 land: overhead screenshots of the edited cells (slope, add, replace, remove) from the frozen scene, then a playthrough with enemies for AC #2, #3 and the visible half of AC #5. Update docs if the playthrough contradicts anything above.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified on macOS/CrossOver with scripts/run.py cycle on a scratch level (Forest seed 20261007): all 7 edits applied with no errors. ReplaceWithSlope at (9,7) East -> (80, 0, 0) yaw 90; remove then AddFlat at (11,7) height 1 -> (160, 20, 0); remove, AddFlat, then ReplaceWithSlope at (12,7) North -> (200, 0, 0) yaw 0; remove at (13,7). Positions equal -280 + 40 * cell, so spacing from MapParameters is right.

Not verified: the one screenshot taken shows the spawn portal, not the edited cells, so the tile changes were confirmed from the log only. AC #5 (visibly changes the tile) stays open for TASK-004.09. AC #2 and #3 need a playthrough with enemies, which the harness cannot drive; whether enemies get stuck on edited terrain or fall into removed-tile holes is unconfirmed, and AC #3 stays open because nothing in the mod keeps enemies off a hole.

AC #1 is checked as not applicable, as approved: no navmesh exists on open maps, so there is nothing to rebuild.

Quit work done alongside: run.py quit now waits for the game process to exit (commit 733fdc5). Dependencies on TASK-004.08 and TASK-004.09 were added so the visual check is possible before this task closes.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
