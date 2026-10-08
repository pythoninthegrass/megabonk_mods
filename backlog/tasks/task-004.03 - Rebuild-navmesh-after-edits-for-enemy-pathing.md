---
id: TASK-004.03
title: 'Support slope and added-tile edits live, and rebuild navigation after edits'
status: In Progress
assignee:
  - Claude
created_date: '2026-10-06 21:42'
updated_date: '2026-10-08 04:29'
labels:
  - level-editor
dependencies:
  - TASK-004.02
  - TASK-004.08
  - TASK-004.09
modified_files:
  - src/MegabonkLevels.Mod/live_edit_patch.cs
  - src/MegabonkLevels.Mod/live_edit_plan.cs
  - src/MegabonkLevels.Mod/tile_placement.cs
  - src/MegabonkLevels.Mod/reachability_validator.cs
  - src/MegabonkLevels.Mod/collision_rebuild.cs
  - src/MegabonkLevels.Mod/fill_regeneration.cs
  - src/MegabonkLevels.Mod/fill_edge_plan.cs
  - src/MegabonkLevels.Mod/kill_floor.cs
  - src/MegabonkLevels.Mod/kill_floor_watcher.cs
  - src/MegabonkLevels.Mod/megabonk_levels_mod.cs
  - src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj
  - tests/MegabonkLevels.Tests/tile_placement_tests.cs
  - tests/MegabonkLevels.Tests/reachability_validator_tests.cs
  - tests/MegabonkLevels.Tests/live_edit_plan_tests.cs
  - tests/MegabonkLevels.Tests/fill_edge_plan_tests.cs
  - tests/MegabonkLevels.Tests/kill_floor_tests.cs
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
- [x] #5 SetTileSlope to a non-None direction from a loaded level file is applied to the live map and visibly changes the tile (correct prefab and orientation)
- [x] #6 AddTile on a cell with no live tile instantiates a tile at the correct world position, with spacing read from StageData.mapParameters at runtime
- [x] #7 Wall and fill pieces next to height, slope, added, or removed tiles are handled consistently, or the remaining visual gap is documented as a known limit
- [x] #8 Pure logic introduced for slope and added-tile handling is unit tested, with the tests written before the implementation
- [x] #9 Replacing a tile with a slope or flat leaves no see-through void: no sky is visible through the replaced cell from above or through the open side of the slope wedge, verified with frozen overhead and angled screenshots
- [x] #10 A kill floor on mod-loaded levels kills the player through the game's own kill API when they fall below the lowest tile, so falling into a removed cell or void ends the run instead of falling forever
- [x] #11 The kill-floor decision (below-floor test and floor height from the level's lowest tile) is pure logic, unit tested with the tests written before the implementation, and documented in docs/development.md or docs/runtime-map-structure.md
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved by Lance. Steps 1-5 are done. TASK-004.08 (freeze) and TASK-004.09 (camera pose) have landed (commits 9a83e85, 283d461), so step 6a is ready; step 6b is still blocked on a surviving player.

1. [done] Observed 40 live Forest slope tiles on macOS/CrossOver: a slope tile is the `slopeTile` prefab at `posY` p, `ProceduralTile.dir` points uphill and the yaw follows it (dir +Z = 0, +X = 90, -Z = 180, -X = 270), and the uphill neighbour is always at p + 1.
2. [done] Wrote failing tests first (tile_placement_tests.cs): slope direction to grid step and back, move/replace/add decision from live occupancy and target TileState, world position from scaledTileWidth/scaledTileHeight. New file tile_placement.cs, registered in the test csproj.
3. [done] Implemented in live_edit_patch.cs: a SetTile that changes tile kind, or lands on an empty cell, instantiates `slopeTile` or `flatTile` through the game's `InstantiateTile(cell, height, prefab, dir, parentDir)`, destroys the old tile, and updates `proceduralTiles[x][z]` and `tiles`. A same-kind SetTile still only moves the tile. AddTile outside the grid logs a warning (out of scope).
4. [done] Reworked ReachabilityValidator to the observed model (SlopeDirection is the uphill side, a slope spans h to h + 1, side edges connect to nothing, tiles connect when facing edge heights match), with its tests rewritten first. This replaced the earlier downhill-on-the-higher-tile assumption.
5. [done] Wall and fill pieces next to edited tiles are not regenerated; documented as a known limit in docs/level-format.md (FillHoles/FillEdges are private whole-grid passes that would duplicate pieces and shift genIds). Navigation: open maps bake no navmesh and enemies use Rigidbody chase, so no rebuild is needed; AC #1 closed as not applicable and documented in docs/runtime-map-structure.md under AC #4.
6. [open] Visual and playthrough verification, split into 6a and 6b below. Update docs if either contradicts anything above.

Harness commands now available, all via scripts/run.py and documented in docs/development.md: `freeze` / `resume` (MyTime.Pause/Unpause; run timer, enemies and player stop, harness still polls and renders, no pause window), `camera X Y Z --rot RX RY RZ` / `camera --clear` (CameraOverride re-applies the pose from OnLateUpdate; clear restores the saved local pose), and `cycle --freeze` / `cycle --camera X Y Z RX RY RZ` (applied after --settle, before the screenshot).

6a. [ready] Visual check for AC #5 and the visible half of the slope/add/replace/remove edits. Launch the game (docs/development.md, Launching under CrossOver), `run.py load <level>`, `run.py freeze`, then pose an overhead camera over the edited cells and `run.py screenshot <out.png>`; read the PNG. Cell (x, z) is at world (-280 + 40x, 20 * height, -280 + 40z). Use camera y about 60-100 with rotation 90 0 0 (looks straight down): fog washes the map out above about 150 and at y=400 the frame is a flat blue field. A rebuilt mod DLL is only picked up on a fresh launch, so run.py quit and relaunch first. Reuse the Forest seed 20261007 scratch level (edits at (9,7), (11,7), (12,7), (13,7)) or rebuild it. Check slope prefab and yaw (dir +Z = 0, +X = 90, -Z = 180, -X = 270), the added tile's position and height, and the removed-tile hole.

6b. [still blocked] AC #2 and #3 need a playthrough where enemies chase a surviving player. Freeze stops the enemies and the camera command does not keep the player alive, so neither helps; both TASK-004.08 and TASK-004.09 say so. The missing piece is an invulnerable or surviving player in the harness, or a manual playthrough with the log read afterwards. That is a scope decision for Lance: ask before creating a follow-up task or adding acceptance criteria. AC #3 also has a known gap: nothing in the mod keeps enemies off a removed-tile hole, so a code change may follow if enemies fall in.

Scope added by Lance after step 6a (void and sky seen under the (9,7) slope and through the (13,7) removal): add fill under replaced tiles, and a Super Mario Bros style kill floor where falling below the map ends the run. Lance said 'maybe' for the kill floor, so keep it as a separate, easily removed component.

7. [open] Investigate what vanilla puts around and under a slope. Log-only probe in the running game: list fillTiles/flatTiles near a vanilla slope (names, positions, rotation, scale), the wall fields on ProceduralTileGeneration (wallFlat, wallLeftUp, wallLeftDown, wallLeftCross) and EFillType values. FillWallSlopeToFlat(heightDifference, position, height, globalDir, isFirstPieceSloped, useEdgeTextures) and InstantiateFillTile are private but per-position, so they may be callable by reflection to close the open side without the whole-grid FillHoles/FillEdges passes (which would duplicate pieces and shift genIds). Fallback: clone an existing fill piece under the replaced cell. Any pieces created must be indexed or tagged so genIds of existing objects do not shift.
8. [open] Implement the fill under replaced tiles in live_edit_patch.cs, tests first for any pure placement logic (which neighbours need a wall, heights).
9. [open] Kill floor: pure KillFloor logic (floor Y = lowest live tile posY minus a margin; ShouldKill(y, floorY)) with tests first, then a throttled check from OnUpdate in mod-loaded levels only that calls PlayerHealth.KillPlayer(); extend to enemies through Enemy.Kill(string) only if the game exposes an enemy registry, otherwise note the limit. Verify in the game by posing the player below the floor is not possible with the harness, so verify by log of the check and a manual walk-off, and say so.
10. [open] Re-run step 6a frames on the scratch level to confirm no sky through (9,7), then update docs/level-format.md known limits and docs/runtime-map-structure.md.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified on macOS/CrossOver with scripts/run.py cycle on a scratch level (Forest seed 20261007): all 7 edits applied with no errors. ReplaceWithSlope at (9,7) East -> (80, 0, 0) yaw 90; remove then AddFlat at (11,7) height 1 -> (160, 20, 0); remove, AddFlat, then ReplaceWithSlope at (12,7) North -> (200, 0, 0) yaw 0; remove at (13,7). Positions equal -280 + 40 * cell, so spacing from MapParameters is right.

Not verified: the one screenshot taken shows the spawn portal, not the edited cells, so the tile changes were confirmed from the log only. AC #5 (visibly changes the tile) stays open for TASK-004.09. AC #2 and #3 need a playthrough with enemies, which the harness cannot drive; whether enemies get stuck on edited terrain or fall into removed-tile holes is unconfirmed, and AC #3 stays open because nothing in the mod keeps enemies off a hole.

AC #1 is checked as not applicable, as approved: no navmesh exists on open maps, so there is nothing to rebuild.

Quit work done alongside: run.py quit now waits for the game process to exit (commit 733fdc5). Dependencies on TASK-004.08 and TASK-004.09 were added so the visual check is possible before this task closes.

Step 6a run (macOS/CrossOver, scratch level Forest seed 20261007, frozen, overhead and angled camera shots). Log: all 7 edits applied, no errors. Seen in the frames: (9,7) slope East is a tilted plane rising toward +X (correct prefab and yaw 90); (11,7) AddFlat at height 1 is a raised flat block; (13,7) removal is a hole that shows sky. AC #5 is checked on the (9,7) slope. The (12,7) North slope was not isolated in any frame, so its orientation is unconfirmed.

Finding: straight-down shots show sky through the east part of cell (9,7), and angled shots show an open triangular void under the slope wedge (no fill under the replaced tile). The (13,7) hole is the intended removal, but a player or enemy that steps off the slope into the void, or into a removed cell, falls through to the sky. This is the visual side of the AC #3 gap (nothing keeps enemies off a hole) and goes beyond the documented wall/fill limit, because the tile that was replaced leaves no ground under it. Whether the slope surface itself is walkable, and whether the void is reachable on foot, is unconfirmed: the harness cannot move the player. Needs Lance's decision on scope (fill under replaced tiles, a kill floor, or document as a known limit).

Steps 7-10 done (macOS/CrossOver, scratch levels). Root cause of the fall-through was not the missing fill but stale ground collision: all ground collision is one baked CombinedCollisionMesh (MeshColliderCombiner.CombineMeshes) that edits never touched, so a removed tile kept an invisible floor and raised or added tiles had almost no collision. Added CollisionRebuild (re-attach each piece's prefab collider mesh, run the game's combiner, swap tileGen.collider); validated by rebuilding an unedited level (413 vertices and bounds identical to the game's own), then by rays on the scratch level (slope y=10, added tile y=20, removed cell open to the world floor).

Fill: FillRegeneration destroys fill pieces on every edge of an edited occupied tile and recreates them with the game's private per-edge FillHole by reflection (FillHole(cell, neighbour) x4 on a vanilla slope reproduces its four wall pieces exactly). Screenshots: the sky through slope cell (9,7) is gone, the slope has side walls, the only remaining hole is the intended (13,7) removal. Edges against removed cells are not touched, so walls around a removed cell stay as they were.

Kill floor: KillFloor (pure, 7 tests written first) and KillFloorWatcher. The game already has a catch floor, a WorldCollider at y=-80 (mesh bounds read 1x1x1, so its transform y is used); the kill floor is the lowest tile level minus 40, clamped to at least 8 above it. Two bugs found by running it: GameObject.Find picked a boundary wall named WorldCollider (armed at y=10 and killed the player at spawn), then collider.bounds was degenerate. Verified with a level that removes all tiles but one: 'armed at y=-40', 'player fell to y=-48.49, killing', death screen. Enemy kills were not observed in game (the player died before any enemy spawned), and the kill floor is armed only for mod-loaded Tiles maps.

AC #2 and #3 stay open: they need a playthrough with enemies on a surviving player. Nothing stops enemies pathing into a hole; the kill floor only ends their fall. Unconfirmed: what the vanilla game does at its own catch floor (PlayerMovement.TeleportPlayerBackToBounds exists, no caller in the dump). The (12,7) North slope orientation is still not isolated in a frame.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
