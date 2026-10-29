---
id: TASK-021.24
title: >-
  Keep bosses and enemies from getting stuck below the level or inside Warehouse
  structures
status: Done
assignee: []
created_date: '2026-10-29 09:13'
updated_date: '2026-10-29T20:17:00Z'
labels:
  - bug
  - enemies
  - thps-warehouse
dependencies: []
references:
  - /Users/lance/Desktop/Screenshot 2026-10-29 at 4.09.48 AM.png
documentation:
  - docs/thps-warehouse-layout.md
  - docs/level-format.md
  - docs/runtime-map-structure.md
  - scripts/build_thps_level.py
  - src/MegabonkLevels.Mod/kill_floor.cs
  - src/MegabonkLevels.Mod/kill_floor_watcher.cs
parent_task_id: TASK-021
priority: medium
ordinal: 117000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
On the THPS Warehouse level, bosses (and some other enemies) end up somewhere the player cannot reach them, which blocks the "Defeat the Boss" objective.

Observed in a playtest (Easy, 10:34 into the run, dev readout on):
- Lil Bark was trapped in the room above the main half pipe. The readout showed the boss at pos(174, 26, 26) while the player was at pos(165, 17, -11), with the kill floor at -60. The boss stayed in the upper room and never reached the player.
- Bosses also get stuck below the level, under the playable area.

Likely causes to investigate: the NavMesh does not connect the upper rooms and structures to the ground, and the outer forest terrain around the Warehouse lets enemies walk or fall off the play area. One option is to remove the outer forest level so the main play area is enclosed. Treat that as a proposal to evaluate, not a decision; the alternative is walls or kill/respawn handling.

Related: TASK-021.11 covers general Warehouse gameplay fit (reachability, vert surfaces, enemies). Reproduce with `relaunch levels/thps.mblevel.json`, and use the dev readout and `query_objects` to find where a boss ends up.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Reproduce a boss stuck in the room above the main half pipe and a boss stuck below the level, and record the positions and cause in docs/development.md or the task notes
- [x] #2 Stage bosses and minibosses spawned on the Warehouse level can path to the player from every spawn point, or are relocated/respawned when they cannot
- [x] #3 No boss ends up below the playable area or inside a Warehouse structure after a full run to the boss fight
- [x] #4 Decision on removing the outer forest terrain versus containing enemies another way is recorded with the reason
- [x] #5 A regression check (Python test or harness command) covers the containment or reachability rule where it can be tested without the game
- [x] #6 Verified in the running game: the boss fight completes on the Warehouse level without a stuck boss
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
## Implementation plan (agreed 2026-10-29)

Decision (AC #4): remove the tile sub-level terrain rather than walling the arena. The Warehouse mesh floats like a native island; the game's own ground-layer spawn raycasts (SpawnPositions, onlyUseGroundLayer + FindHitClosestToPlayerY) then force enemy and boss spawns onto the Warehouse floor. Explicit killFloorY replaces tile-derived arming.

1. Reproduce (AC #1): run the current level with MEGABONK_KILL_FLOOR_HEARTBEAT=1; record positions/causes in task notes. Evidence so far: boss Ent1 (Lil Bark) spawned at pos(174, 26, 26) inside the hanging box; the relocated BossSpawner sits at (170, 15.6, 27), so the boss materialises in the box and EnemyMovementRb (physics chase, no NavMesh on Tiles maps) cannot get out. Kill floor (-60) is irrelevant at y=26.
2. Mod: optional killFloorY float in the level file (additive, schemaVersion stays 3; same convention as maxSlopeAngle/noGrass).
   - src/MegabonkLevels.Mod/level_file.cs + serialization: optional field, round-trip.
   - src/MegabonkLevels.Mod/kill_floor.cs: Unity-free FloorYExplicit(killFloorY, catchFloorY): explicit value clamped to stay above catch floor + CatchFloorClearance.
   - src/MegabonkLevels.Mod/kill_floor_watcher.cs: arm from the explicit value when present; tile-derived stays the fallback.
   - src/MegabonkLevels.Mod/live_edit_patch.cs: thread the value into KillFloorWatcher.Arm (call site line ~444).
3. scripts/build_thps_level.py: keep exactly one tile (generated spawn cell (10,7), level -1, hidden under the mesh); delete the 4x7 inner + raised ring ops; write killFloorY computed from the mesh's lowest collider point (scripts/warehouse_surface.py) minus a margin; move the BossSpawner to ground level (same xz (170, 27), y = mesh floor there, BottomPiece + Collider still hidden).
4. Tests: tests/MegabonkLevels.Tests (killFloorY round-trip, FloorYExplicit clamp, thps level keeps one tile at the spawn cell, carries killFloorY, spawner on the floor) and tests/test_build_thps_level.py (op counts, killFloorY bound, spawner payload).
5. Verify in game (AC #2/#3/#6): task mod:build, relaunch(levels/thps.mblevel.json), boss fight completes, readout shows the boss on the floor, heartbeat tracks stageBosses. Watch for spawns landing on the Warehouse roof.
6. Docs (AC #4, DoD): level-format.md killFloorY row; thps-warehouse-layout.md enclosure/spawner sections + the recorded decision and reason.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## Verified in game (2026-10-29, build 21750826, levels/thps.mblevel.json regenerated)

Kill floor: `KillFloor: armed at y=-35 (authored, catch floor y=-80)` in MelonLoader/Latest.log, and the on-screen readout shows `floor -35`.

Enemies land on the Warehouse mesh, not below it. With spawns on, 35 heartbeat samples up to 9 enemies: lowest enemy collider y ranged -4.933 (the main half pipe's floor) to 0.5; nothing ever went below -20, let alone toward -35. The sub-level terrain is gone, so there is no second ground under the mesh to catch anything.

Boss: interacted with the portal at (150, 0.5, 65) in play mode (E, held ~300 ms through a CoreGraphics key event) and stage boss Lil Bark (Enemy1, id 195/0, maxHp 7366.5) materialised standing on the mesh floor — heartbeat `stageBosses=1 ... lowest=0.5`, then 0.500-1.681 throughout the fight, i.e. the same floor the player stands on, not the hanging box at y=25.75. It chased and hit the player. Killing it with player damage took the run to `TIER 1 COMPLETED` (evidence PNG .tools/evidence/021-24-tier-completed.png); the death screen's damage panel totalled Mirror 4,031 + Wireless Dagger 3,294 + Zap 48 = 7,373 damage with Kills: 1, so the boss died to the player's weapons and not to the kill floor.

Evidence PNGs: .tools/evidence/021-24-open.png, -portal.png, -portal-invuln.png, -at-portal.png, -readout.png, -boss.png, -fight.png, -boss-dead.png, -tier-completed.png, -quests2.png.

## Reproduced (AC #1, 2026-10-29 playtest, build 21750826)

- Boss in the hanging box: readout showed Lil Bark (Ent1) at pos(174, 26, 26) while the player was at pos(165, 17, -11) and the readout floor at -60 (evidence: /Users/lance/Desktop/Screenshot 2026-10-29 at 4.09.48 AM.png). Cause: the level file's `object.move` had relocated the `gen:object:BossSpawner:0000` itself to (170, 15.6, 27) inside that glass box, so the boss materialises there. Tiles maps bake no NavMesh (`NavMeshSurface` exists but is not baked for the mod's edited grid) and `EnemyMovementRb` chases with rigidbody velocity, so it cannot climb out; the kill floor at -60 never applies at y=26 and "Defeat the Boss" cannot complete.
- Boss/enemies below the playable area: the level's tile sub-level (inner 4x7 block flat at level -1 plus a one-cell ring at level 2) put a second ground under and around the Warehouse mesh. The game's spawn raycasts (`SpawnPositions`, onlyUseGroundLayer + `FindHitClosestToPlayerY`) accepted hits on that terrain, so actors landed under the mesh, and the kill floor derived from that terrain sat at y=-60 — under the mesh's own sub-floor skirt, where a body could come to rest above it and stay unkillable.

## Containment decision (AC #2/#4)

Removed the tile sub-level instead of walling the arena (`WALL_LEVELS`/`ring_cells` deleted; `kept_cells()` is the single generated spawn cell). The Warehouse mesh now floats like a native island, so the only ground-layer surface is the mesh itself and every spawn lands on it. Verified: with the player on the south upper deck, spawned enemies stood on the same surface at y=27.8 and engaged; with the player on the main floor they stood at y=0.5 to -4.9 (the main half pipe's floor). Nothing spawned under the mesh; the authored kill floor at y=-35 ends any fall, and it sits above the mesh's lowest geometry (-48.6) so a body cannot rest on the sub-floor skirt out of reach.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Enemies and the stage boss now stay on the Warehouse mesh, and the boss fight finishes a run.

Removed the level tile sub-level (scripts/build_thps_level.py): `WALL_LEVELS` and `ring_cells()` are gone and `kept_cells()` returns only the generated spawn cell (10,7) at level -1, so the 15x15 grid is empty ground plus one hidden tile under the mesh. The Warehouse now floats like a native island and the only ground-layer surface is the mesh itself, so the game spawn raycasts (`SpawnPositions`, onlyUseGroundLayer + `FindHitClosestToPlayerY`) put every enemy and boss on the floor the player is standing on. Containment comes from the mesh own walls; no walls were added.

Added `killFloorY` to the level format and the mod (`LevelFile.KillFloorY`, `KillFloor.FloorYExplicit`, `KillFloorWatcher.Arm(tileGen, logger, killFloorY)`, threaded through `LiveEditPatch.SetPendingEdits` and `LevelLoaderPatch`). The field is optional and additive, so `schemaVersion` stays 3, and an authored value is still clamped above the game catch floor + clearance. The level authors -35 (`KILL_FLOOR_Y`): below the kept tile, above the mesh lowest point (-48.6), well clear of the catch floor at -80. Deriving from the single remaining tile would have given -60, deep enough for a body to rest on the mesh outer skirt and stay unkillable.

Moved the boss portal out of the hanging glass box: it stands on the flat Warehouse floor at the south deck of the main half pipe, world (150, 0.5, 65) (`BOSS_SPAWN_LOCAL`), with its height raycast from `BOSS_SPAWN_DROP_FROM` = 12 - under the box, so the box can never catch it. The portal had been relocated to (170, 15.6, 27) inside that box, so the boss materialised there and `EnemyMovementRb`, chasing with rigidbody physics on a Tiles map that bakes no NavMesh, could not get out.

Verification: task check green - 1243 mod tests (11 new: `FloorYExplicit` cases, `killFloorY` round-trip/absent/inequality, and thps checks that only the spawn cell survives, that the kept tile sits above the kill floor, and that the boss spawner payload stands on the floor) and 490 python tests, lint clean. In game (build 21750826): `KillFloor: armed at y=-35 (authored, catch floor y=-80)`; 35 heartbeat samples with up to 9 live enemies put the lowest enemy collider between -4.933 and 0.5, nothing under -20. Pressing E at the portal spawned Lil Bark standing on the floor (`stageBosses=1 ... lowest=0.5`, then 0.5-1.68 throughout), it chased and hit the player, and killing it with player weapons reached TIER 1 COMPLETED - the death screen panel totalled 7,373 damage against the boss 7,366 HP with Kills: 1, so the kill floor was not involved. Evidence PNGs in .tools/evidence/021-24-*.png.

Risks and follow-ups: the mesh north edge is open, so a knocked-off player or enemy falls to the kill floor rather than being walled in; `KillFloorWatcher` kills the player through `KillPlayer()`, which bypasses the harness `invulnerable` patch (only `TakeDamage` is patched) - the harness player died twice that way. Enemies do spawn on upper decks when the player stands on one (y=27.8 at the start half-pipe deck) and chase from there; that is the game own near-player ground spawn and it was not exercised down to the main floor in every combination. TASK-021.11 still covers general Warehouse gameplay fit.
<!-- SECTION:FINAL_SUMMARY:END -->
