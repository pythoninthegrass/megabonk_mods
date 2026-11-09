---
id: TASK-021.25
title: Spawn the boss outside the hanging box while the boss portal stays inside it
status: Done
assignee: []
created_date: '2026-10-29T20:57:00Z'
updated_date: '2026-10-29T21:21:00Z'
labels:
  - thps-warehouse
  - mod
  - enemies
  - boss
dependencies: []
documentation:
  - docs/thps-warehouse-layout.md
  - docs/level-format.md
  - docs/thps-warehouse.md
  - src/MegabonkLevels.Mod/rail_wall_end_patch.cs
  - src/MegabonkLevels.Mod/boss_spawn_redirect.cs
  - src/MegabonkLevels.Mod/boss_spawn_redirect_patch.cs
  - tests/MegabonkLevels.Tests/boss_spawn_redirect_tests.cs
parent_task_id: TASK-021
priority: medium
type: feature
ordinal: 119000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The boss portal on the THPS Warehouse level should sit inside the hanging glass box above the main half pipe, hidden in plain sight the way the reference map has it (docs/thps-warehouse.md, Glass corridor and secret room: the skater reaches the box by launching off the quarter pipe in front). TASK-021.24 moved the portal out of the box onto the floor because a portal spawns its boss at its own position and the boss, chasing with rigidbody physics on a Tiles map that bakes no NavMesh, could not get out of the box, so the Defeat the Boss objective could not complete.

Restore the portal to the box and relocate only the boss. EnemyManager.SpawnBoss(EEnemy eEnemy, int summonerId, EEnemyFlag enemyFlag, Vector3 pos, float extraSizeMultiplier = 1) takes the spawn position as a parameter (dump.cs:364151), and InteractableBossSpawner : BaseInteractable (dump.cs:333417) passes the spawner transform through it from its Interact() override - which is why moving the spawner moved the boss. A Harmony prefix on SpawnBoss that rewrites pos, armed only while the level's own boss spawner is being interacted with, keeps the portal and its VFX in the box and materialises the boss on reachable ground.

Shape of the change: one optional additive level field for the boss spawn position (schemaVersion stays 3, same convention as killFloorY and maxSlopeAngle); a patch pair modelled on RailWallEndPatch (nested HarmonyPatch classes, gated on CustomLevelState.IsActive) with the decision logic in a Unity-free file so it is testable; the generator restoring BOSS_SPAWN_LOCAL to the box and computing the boss position with warehouse_surface.drop so the boss lands on the main half pipe floor under the box.

Mesh facts (scripts/warehouse_surface.py against the extracted mesh): the box is a closed room - interior floor top y=15.64 (slab underside 15.31), roof underside y=25.42 (roof top 25.75), walls on all four sides between them, over footprint x 149.4-178.9, z 20.9-31.4. An earlier reading of an interior floor at 25.753 with no ceiling over the west half was wrong: that surface is the roof. The main half pipe floor is y=-4.933 and its coping lip runs at y=8.56. The drop for the boss position must start below the box's floor slab (15.31), otherwise the box catches it - the mistake that caused TASK-021.24.

Out of scope, follow-up: whether a skater can actually launch from the 8.56 coping into the closed box about 7 units above the interior floor. That needs OS-level keyboard input because the harness injects only EditorInput. Whether the portal is reachable does not change this task: the redirect must work so that once reachability is settled, activation produces a fightable boss.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The level file carries an optional boss spawn position, round-trips through the serializer, and keeps schemaVersion 3
- [x] #2 Interacting with the Warehouse boss portal inside the hanging box spawns the stage boss on the main half pipe floor, and the boss can reach and fight the player there
- [x] #3 Only the custom level's own boss spawner is redirected: summoned bosses and other SpawnBoss callers keep their positions, and a level without the field behaves exactly as before
- [x] #4 Decision logic lives in a Unity-free file with tests written first, and the mod logs the redirect with both positions
- [x] #5 The generator keeps the portal in the box (BottomPiece and Collider still hidden) and derives the boss position from a drop that starts below the box underside, with Python tests covering both
- [x] #6 Verified in the running game: the boss spawns on the pipe floor after pressing E at the in-box portal, and killing it completes the tier
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
Agreed 2026-10-29 after research. Keep the BossSpawner in the hanging box; move only the boss at activation time.
Research findings. EnemyManager (Il2CppAssets.Scripts.Managers.EnemyManager) has SpawnBoss(EEnemy, int, EEnemyFlag, Vector3 pos, float) at dump.cs:364151 and two SpawnEnemy overloads; InteractableBossSpawner : BaseInteractable (dump.cs:333417) has public override bool Interact(). The boss's spawn position arrives as a by-value argument, so a Harmony prefix cannot rewrite it - the postfix is the hook: it can read pos and reposition the returned Enemy. InteractableBossSpawner also exposes public static Action A_BossSpawned, and Enemy has public Rigidbody rb, public CapsuleCollider collider, plus a private StartTeleporting(Vector3) and public TeleportToPlayer() (the game already teleports enemies that fall too far behind).
Offset handling. When the portal stood on the floor at y=0.5 the boss's pivot settled at 12.39 and 13.57 while its collider bottom sat at 0.5 and 1.68, so the pivot is about 11.9 above the collider bottom. Do not hardcode that: in the postfix compute offset = actualPosition - pos and place the boss at anchor + offset, so the boss's feet land on the authored surface whatever the game's own placement does.
1. src/MegabonkLevels.Mod/level_file.cs: add IReadOnlyList<float> BossSpawnPosition = null plus equality. Additive, so schemaVersion stays 3; System.Text.Json camelCase covers (de)serialization in level_file_serialization.cs.
2. New src/MegabonkLevels.Mod/boss_spawn_redirect.cs, Unity-free like kill_floor.cs: IsUsablePosition(IReadOnlyList<float>) (three finite components), ShouldArm(active, position), ShouldConsume(armedFrame, frame, windowFrames, window 2), Placement(anchor, spawnPos, actualPos) => anchor + (actualPos - spawnPos). Linked into tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj.
3. New src/MegabonkLevels.Mod/boss_spawn_redirect_patch.cs, modelled on rail_wall_end_patch.cs: nested HarmonyPatch classes. Prefix on InteractableBossSpawner.Interact arms the redirect with Time.frameCount when CustomLevelState.IsActive and a usable position is authored. Postfix on EnemyManager.SpawnBoss, and on the SpawnEnemy(EnemyData, Vector3, int, ...) overload as a fallback in case the spawner goes through it, consumes the arming once, moves __result.transform and __result.rb to Placement(...) and zeroes rb.velocity. Logs BossSpawnRedirect: boss moved from (x, y, z) to (x, y, z). Disarm() clears the flag, called when a generation applies its edits so a stale arming can never move an unrelated boss.
4. src/MegabonkLevels.Mod/live_edit_patch.cs: hold _bossSpawnPosition in SetPendingEdits, expose it, include it in the editor-save round trip, and call BossSpawnRedirectPatch.Disarm() where the kill floor arms. src/MegabonkLevels.Mod/level_loader_patch.cs passes level.BossSpawnPosition. Register BossSpawnRedirectPatch.Install(LoggerInstance) in megabonk_levels_mod.cs.
5. scripts/build_thps_level.py: restore BOSS_SPAWN_LOCAL to the box (150, 167) with BOSS_SPAWN_Y 15.6, scale 0.4, yaw 90, hiddenChildren BottomPiece and Collider. Add BOSS_GROUND_LOCAL and BOSS_GROUND_DROP_FROM = 12.0, under the box's floor slab at 15.31 so the box cannot catch the drop, and emit bossSpawnPosition from warehouse_surface.drop onto the main half pipe floor (y=-4.933 there). Regenerate levels/thps.mblevel.json.
6. Tests first: tests/MegabonkLevels.Tests/boss_spawn_redirect_tests.cs for the pure helpers including the offset case; level_file_tests.cs for the round trip, absent field and inequality; thps_level_tests.cs for the spawner back in the box, bossSpawnPosition present, below the box underside, above killFloorY; tests/test_build_thps_level.py for the portal payload and the emitted anchor.
7. Verify in game: task mod:build, relaunch levels/thps.mblevel.json, and activate the in-box portal. Confirmed 2026-10-29 with the user driving the game (the harness injects only EditorInput, so portal activation needs real input): the log carries `BossSpawnRedirect: armed for (170, -4.933, 20) at frame 8582.` then `BossSpawnRedirect: boss moved from (176.227, 27.49, 30.725) to (170, 6.957, 20) via SpawnEnemy.`, a KillFloor heartbeat read the boss's collider bottom at -2.78 on the pipe floor (pivot 9.11), and after the user killed him the watch reported `stageBosses=0` (the user confirmed the kill; the tier-completion banner is on-screen only, not a log line). Only the SpawnEnemy postfix fired; the SpawnBoss patch stayed belt-and-braces. Reaching the box by skating remains unverified and is tracked separately.
8. Docs: docs/level-format.md got the bossSpawnPosition row; docs/thps-warehouse-layout.md got the restored box position, the box's closed-room geometry, the redirect mechanism and the authored boss anchor; docs/thps-warehouse.md notes in "Glass corridor and secret room" that the mesh makes the box a closed room and that whether a skater can get in is unproven.
Risks. Whether the spawner calls SpawnBoss or one of the SpawnEnemy overloads is unconfirmed from the dump alone; both are patched and the log says which one fired. If the game spawns asynchronously from Interact, the two-frame window will miss it and the log will show an armed redirect that never consumed - widen the window or switch to the A_BossSpawned callback in that case. Repositioning a pooled enemy without the game's own StartTeleporting skips the dissolve effect; acceptable if the boss ends up standing on the pipe floor.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The boss portal stands inside the hanging glass box at its committed placement, world (170, 15.6, 27), and the level authors where its boss appears instead.

New: level_file.cs gains an optional bossSpawnPosition (float[3], additive, schemaVersion stays 3) with equality, serializer coverage and an editor-save round trip; boss_spawn_redirect.cs holds the Unity-free decision logic (IsUsablePosition, ShouldArm, ShouldConsume, Placement); boss_spawn_redirect_patch.cs arms from a prefix on InteractableBossSpawner.Interact and repositions from a postfix on the positional SpawnEnemy overload, with a SpawnBoss postfix as belt-and-braces. Placement keeps the game's own offset between the spawn point and the boss's feet, so the authored value is a point on the floor the boss should stand on. LiveEditPatch passes the field and disarms the redirect when a generation completes; LevelLoaderPatch passes it through; the patch installs from megabonk_levels_mod.cs.

The generator restores BOSS_SPAWN_LOCAL (150, 167) / BOSS_SPAWN_Y 15.6 for the portal and emits bossSpawnPosition from a ws.drop starting at BOSS_GROUND_DROP_FROM 12.0, below the box's floor slab, onto the main half pipe floor: world (170, -4.933, 20), outside the box's south wall in the portal's own x column. levels/thps.mblevel.json regenerated; the portal payload is byte-identical to the pre-redirect commit.

Verification, with the user driving the game (portal activation needs real input, the harness injects only EditorInput): log shows BossSpawnRedirect: armed for (170, -4.933, 20) at frame 8582 then boss moved from (176.227, 27.49, 30.725) to (170, 6.957, 20) via SpawnEnemy - only the SpawnEnemy postfix fired. A KillFloor heartbeat read the boss's collider bottom at -2.78 (pivot 9.11), standing on the pipe floor well above the -35 kill floor; the user fought and killed him and the watch reported stageBosses=0.

Mesh facts corrected: the box is a closed room (interior floor top 15.64, slab underside 15.31, roof underside 25.42, roof top 25.75, walls on all four sides), not the open-west-end room an earlier reading claimed; the boss drop therefore starts below 15.31. Whether a skater can actually get into the box from the 8.56 coping is still unverified and tracked separately.

Tests: 3 new in boss_spawn_redirect_tests.cs plus the existing suite for the pure helpers, 3 in level_file_tests.cs (round trip, absent field, inequality), 2 in thps_level_tests.cs (portal in the box, boss anchor below the slab and above the kill floor), 6 in tests/test_build_thps_level.py. task check green: 494 python, 1257 mod tests, lint clean.

Docs: docs/level-format.md gained the bossSpawnPosition row, docs/thps-warehouse-layout.md the portal placement, box geometry and boss anchor, docs/thps-warehouse.md the closed-room note.
<!-- SECTION:FINAL_SUMMARY:END -->
