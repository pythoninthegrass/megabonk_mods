---
id: TASK-004.03
title: 'Support slope and added-tile edits live, and rebuild navigation after edits'
status: Done
assignee:
  - Claude
created_date: '2026-10-06 21:42'
updated_date: '2026-11-09 05:26'
labels:
  - level-editor
dependencies:
  - TASK-004.02
  - TASK-004.08
  - TASK-004.09
  - TASK-004.10
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

TASK-002.03 found that the open Tiles and ProceduralMesh maps (Forest, Desert) bake no navmesh at all, and enemy movement (EnemyMovementRb) is direct Rigidbody-based chase toward the player. The only NavMeshSurface bake is the Graveyard crypt/boss dungeon (RsgController.navmeshSurface.BuildNavMesh()). So for the open maps this part may reduce to confirming that enemies physically traverse edited terrain, and for removed tiles, keeping them off holes. If the mechanism turns out to be substantially harder than expected, flag the risk to the maintainer rather than shipping a level editor where enemies get stuck on edited terrain.

Verify with a real playthrough: edit a level to add a new path, or let enemies naturally path toward the player across an edited tile, and confirm no enemies become stuck.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Navigation data is rebuilt/rebaked after edits are applied, using whatever mechanism TASK-002.03 confirmed the game actually uses
- [x] #2 Enemies successfully path onto added or height/slope-modified tiles in a real playthrough
- [x] #3 Enemies that enter a removed cell are killed by the kill floor, including tall actors such as the stage boss, and each is killed once, verified in a real playthrough
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
Approved by the maintainer. Steps 1-10 are done; what remains is step 6b (AC #2 and #3), blocked on a surviving player in the harness. TASK-004.08 (freeze) and TASK-004.09 (camera pose) landed in 9a83e85 and 283d461; the collision, fill and kill-floor work is in 2ad3392.

1. [done] Observed 40 live Forest slope tiles on macOS/CrossOver: a slope tile is the `slopeTile` prefab at `posY` p, `ProceduralTile.dir` points uphill and the yaw follows it (dir +Z = 0, +X = 90, -Z = 180, -X = 270), and the uphill neighbour is always at p + 1.
2. [done] Wrote failing tests first (tile_placement_tests.cs): slope direction to grid step and back, move/replace/add decision from live occupancy and target TileState, world position from scaledTileWidth/scaledTileHeight. New file tile_placement.cs, registered in the test csproj.
3. [done] Implemented in live_edit_patch.cs: a SetTile that changes tile kind, or lands on an empty cell, instantiates `slopeTile` or `flatTile` through the game's `InstantiateTile(cell, height, prefab, dir, parentDir)`, destroys the old tile, and updates `proceduralTiles[x][z]` and `tiles`. A same-kind SetTile still only moves the tile. AddTile outside the grid logs a warning (out of scope).
4. [done] Reworked ReachabilityValidator to the observed model (SlopeDirection is the uphill side, a slope spans h to h + 1, side edges connect to nothing, tiles connect when facing edge heights match), with its tests rewritten first.
5. [done] Navigation: open maps bake no navmesh and enemies use Rigidbody chase, so no rebuild is needed; AC #1 closed as not applicable and documented in docs/runtime-map-structure.md. The earlier "wall and fill pieces are not regenerated" limit is superseded by steps 7-8.
6a. [done] Visual check on the Forest seed 20261007 scratch level with the harness freeze and camera commands (see docs/development.md): slope (9,7) East is a ramp rising toward +X, (11,7) is a raised flat block, (13,7) is a hole. Cell (x, z) is at world (-280 + 40x, 20 * height, -280 + 40z); use camera y about 60-100 looking straight down (rotation 90 0 0) because fog washes the map out above about 150. A rebuilt mod DLL needs a fresh launch (run.py quit, relaunch). The (12,7) North slope was not isolated in a frame.
6b. [blocked] AC #2 and #3 need a playthrough where enemies chase a surviving player. Freeze stops the enemies and the camera command does not keep the player alive. The missing piece is an invulnerable or surviving player in the harness, or a manual playthrough with the log read afterwards. That is a scope decision for the maintainer: ask before creating a follow-up task or adding acceptance criteria. Nothing stops enemies pathing into a hole; the kill floor only ends their fall.

Scope added by the maintainer after 6a (sky seen under the (9,7) slope and through the (13,7) removal): fill under replaced tiles, and a Super Mario Bros style kill floor.

7. [done] Investigated what vanilla builds around a slope. Root cause of the fall-through was stale ground collision, not only missing fill: all ground collision is one baked `CombinedCollisionMesh` that edits never touched. The game's private per-edge `FillHole(from, to)` reproduces the vanilla wall pieces exactly (four pieces on a vanilla slope cell).
8. [done] Fill and collision. `FillEdgePlan` (pure, tests first) lists the edges to regenerate; `FillRegeneration` destroys the fill pieces on those edges and calls `FillHole` both ways by reflection; `CollisionRebuild` re-attaches each live piece's prefab collider mesh, runs `MeshColliderCombiner.CombineMeshes`, and swaps `tileGen.collider`. `LiveEditPlan.ChangesTerrain` (tests first) gates both.
9. [done] Kill floor. `KillFloor` (pure, tests first) and `KillFloorWatcher`: floor is the lowest live tile level times `scaledTileHeight` minus 40, clamped to at least 8 above the game's own catch floor (`WorldCollider`, y=-80); checked every 0.25 s in mod-loaded Tiles maps; kills the player through `PlayerHealth.KillPlayer()` and enemies through `Enemy.Kill("KillFloor")`. Verified for the player; enemy kills not observed in game.
10. [done] Re-ran the scratch level: no sky through (9,7), slope has side walls, ground rays match the edits. Docs updated in level-format.md and runtime-map-structure.md.

Step 6b is now tracked by TASK-004.10 (harness player invulnerability command). Once it lands: load a scratch level with added, raised and sloped tiles plus a removed one, enable invulnerability, let enemies chase for a while, and read the log and screenshots for AC #2 (enemies reach added/raised/sloped tiles) and AC #3 (enemies do not walk into the removed cell, or are killed by the kill floor if they do). Check the kill-floor enemy path in the same run, since no enemy kill has been observed in game yet.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified on macOS/CrossOver with scripts/run.py cycle on a scratch level (Forest seed 20261007): all 7 edits applied with no errors. ReplaceWithSlope at (9,7) East -> (80, 0, 0) yaw 90; remove then AddFlat at (11,7) height 1 -> (160, 20, 0); remove, AddFlat, then ReplaceWithSlope at (12,7) North -> (200, 0, 0) yaw 0; remove at (13,7). Positions equal -280 + 40 * cell, so spacing from MapParameters is right.

Not verified: the one screenshot taken shows the spawn portal, not the edited cells, so the tile changes were confirmed from the log only. AC #5 (visibly changes the tile) stays open for TASK-004.09. AC #2 and #3 need a playthrough with enemies, which the harness cannot drive; whether enemies get stuck on edited terrain or fall into removed-tile holes is unconfirmed, and AC #3 stays open because nothing in the mod keeps enemies off a hole.

AC #1 is checked as not applicable, as approved: no navmesh exists on open maps, so there is nothing to rebuild.

Quit work done alongside: run.py quit now waits for the game process to exit (commit 733fdc5). Dependencies on TASK-004.08 and TASK-004.09 were added so the visual check is possible before this task closes.

Step 6a run (macOS/CrossOver, scratch level Forest seed 20261007, frozen, overhead and angled camera shots). Log: all 7 edits applied, no errors. Seen in the frames: (9,7) slope East is a tilted plane rising toward +X (correct prefab and yaw 90); (11,7) AddFlat at height 1 is a raised flat block; (13,7) removal is a hole that shows sky. AC #5 is checked on the (9,7) slope. The (12,7) North slope was not isolated in any frame, so its orientation is unconfirmed.

Finding: straight-down shots show sky through the east part of cell (9,7), and angled shots show an open triangular void under the slope wedge (no fill under the replaced tile). The (13,7) hole is the intended removal, but a player or enemy that steps off the slope into the void, or into a removed cell, falls through to the sky. This is the visual side of the AC #3 gap (nothing keeps enemies off a hole) and goes beyond the documented wall/fill limit, because the tile that was replaced leaves no ground under it. Whether the slope surface itself is walkable, and whether the void is reachable on foot, is unconfirmed: the harness cannot move the player. Needs the maintainer's decision on scope (fill under replaced tiles, a kill floor, or document as a known limit).

Steps 7-10 done (macOS/CrossOver, scratch levels). Root cause of the fall-through was not the missing fill but stale ground collision: all ground collision is one baked CombinedCollisionMesh (MeshColliderCombiner.CombineMeshes) that edits never touched, so a removed tile kept an invisible floor and raised or added tiles had almost no collision. Added CollisionRebuild (re-attach each piece's prefab collider mesh, run the game's combiner, swap tileGen.collider); validated by rebuilding an unedited level (413 vertices and bounds identical to the game's own), then by rays on the scratch level (slope y=10, added tile y=20, removed cell open to the world floor).

Fill: FillRegeneration destroys fill pieces on every edge of an edited occupied tile and recreates them with the game's private per-edge FillHole by reflection (FillHole(cell, neighbour) x4 on a vanilla slope reproduces its four wall pieces exactly). Screenshots: the sky through slope cell (9,7) is gone, the slope has side walls, the only remaining hole is the intended (13,7) removal. Edges against removed cells are not touched, so walls around a removed cell stay as they were.

Kill floor: KillFloor (pure, 7 tests written first) and KillFloorWatcher. The game already has a catch floor, a WorldCollider at y=-80 (mesh bounds read 1x1x1, so its transform y is used); the kill floor is the lowest tile level minus 40, clamped to at least 8 above it. Two bugs found by running it: GameObject.Find picked a boundary wall named WorldCollider (armed at y=10 and killed the player at spawn), then collider.bounds was degenerate. Verified with a level that removes all tiles but one: 'armed at y=-40', 'player fell to y=-48.49, killing', death screen. Enemy kills were not observed in game (the player died before any enemy spawned), and the kill floor is armed only for mod-loaded Tiles maps.

AC #2 and #3 stay open: they need a playthrough with enemies on a surviving player. Nothing stops enemies pathing into a hole; the kill floor only ends their fall. Unconfirmed: what the vanilla game does at its own catch floor (PlayerMovement.TeleportPlayerBackToBounds exists, no caller in the dump). The (12,7) North slope orientation is still not isolated in a frame.

Step 6b harness run (macOS/CrossOver, scratch level Forest seed 20261007 with slope (9,7) East, raised flat (11,7), North slope (12,7), removed (13,7)): all 7 edits applied, kill floor armed at y=-72, player invulnerable for about 45 s with 72/72 health and 19 kills, no errors. The idle player stayed at spawn and the mod logs no enemy positions, so nothing was observed about enemies on or near the edited cells. AC #2 and #3 stay open pending the maintainer's manual playthrough and log.

Kill-floor playthrough on the scratch level (macOS/CrossOver, manual, the maintainer playing). Run 1: 67 distinct enemies killed in about 3 minutes (480 log lines, each enemy re-killed about 7 times because a killed enemy stays in EnemyManager.enemies); Lil Bark and a golem were not killed. Run 2 with KillTracker (2 s retry window): enemies logged once each, positions at x 215 to 283, z -41 to 30, nearly all inside the removed tile (13,7); a few at z -27 to -41 and one at (283, 30) drifted while falling. Heartbeat showed the stage boss is in stageBosses and in enemies as 'Enemy1(Clone)', so only its id marks it, and its transform pivot stopped at about y=-66.5, above the floor at -72, while it climbed back out. Fix: KillFloor.LowestPoint compares the lower of the pivot and the Enemy.collider bottom. Run 3: boss id=116 killed at 00:46:31 with pivot y=-63.4 and lowest=-76.29, no retries, no errors. Not yet separately confirmed: the golem. AC #2 and #3 are not checked: enemies do walk into the removed cell and the kill floor ends them, but nothing keeps them out of it, and no run has yet confirmed enemies traverse the added, raised and sloped tiles.

AC #2 checked on the maintainer's first-hand report from the manual playthroughs: enemies crossed the added, raised and sloped tiles without sticking. The mod logs no enemy positions on those tiles, so there is no log evidence for it; the dev readout in TASK-008.03 would give some.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Slope and added-tile edits now apply live (correct prefab, yaw and world position from MapParameters), with wall and fill pieces regenerated through the game's own FillHole and the baked ground collision rebuilt, so edited terrain and removed tiles behave physically. Open maps bake no navmesh and enemies chase by Rigidbody, so no navigation rebuild exists or is needed (documented). A kill floor ends falls into removed cells: the player through PlayerHealth.KillPlayer and enemies through Enemy.Kill, with KillTracker preventing repeat kills and KillFloor.LowestPoint using the collider bottom so tall actors such as the stage boss are killed. Verified in manual playthroughs: dozens of enemies and the boss killed in the removed cell, no errors, no retries. Known limit: the golem was not confirmed separately, and the claim that enemies cross the added, raised and sloped tiles without sticking rests on the playtester's observation, not on logged positions.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
