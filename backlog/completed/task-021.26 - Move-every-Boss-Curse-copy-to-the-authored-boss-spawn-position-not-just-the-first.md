---
id: TASK-021.26
title: >-
  Move every Boss Curse copy to the authored boss spawn position, not just the
  first
status: Done
assignee: []
created_date: '2026-11-02T04:15:00Z'
updated_date: '2026-11-03 04:16'
labels:
  - thps-warehouse
  - mod
  - enemies
  - boss
dependencies: []
documentation:
  - docs/level-format.md
  - docs/thps-warehouse-layout.md
  - src/MegabonkLevels.Mod/boss_spawn_redirect.cs
  - src/MegabonkLevels.Mod/boss_spawn_redirect_patch.cs
  - tests/MegabonkLevels.Tests/boss_spawn_redirect_tests.cs
modified_files:
  - src/MegabonkLevels.Mod/boss_spawn_redirect.cs
  - src/MegabonkLevels.Mod/boss_spawn_redirect_patch.cs
  - src/MegabonkLevels.Mod/live_edit_patch.cs
  - tests/MegabonkLevels.Tests/boss_spawn_redirect_tests.cs
  - docs/development.md
  - docs/level-format.md
  - docs/thps-warehouse-layout.md
parent_task_id: TASK-021
priority: medium
type: bug
ordinal: 134000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The boss spawn redirect moves only the first boss a portal summons: MoveIfArmed (boss_spawn_redirect_patch.cs) consumes the arming on the first SpawnBoss/SpawnEnemy postfix (_armedFrame = null). The game's Boss Curse (InteractableShrineCursed, GameManager.bossCurses) makes the same InteractableBossSpawner.Interact() summon 1 + bossCurses bosses through the same call path, so the second Lil Bark is left at the spawner: the game lifts it to about (176, 27.5, 31) and it lands on the glass box roof (top y=25.75), unreachable, blocking "Defeat the Boss".

Confirmed in a live playthrough (2026-10-31): the redirected first boss stood on the main half pipe floor while the curse copy sat on top of the box.

Placement preserves only the game's vertical lift, so moving every copy as-is would stack them all at the exact anchor. The game staggers copies laterally around the spawner (BaseInteractable.GetOffset: the redirect log shows requested x 176.2 against spawner x 170); reuse that stagger so copies land apart.

Shape of the change: arm with expectedMoves = 1 + GameManager.Instance.bossCurses (clamped); move every boss-flagged spawn within the arming window until the count is met or the window expires (expiry clears the arming and logs once); spread each subsequent copy by the clamped XZ delta of the game's own requested positions against the first boss's; gate each move on Enemy.IsBoss(). Decision logic stays Unity-free in boss_spawn_redirect.cs with tests written first; the patch stays thin.

Fallbacks, decided by in-game verification: if a curse copy spawns outside the two-frame window (FX-staggered), widen the window bounded (the expected-count close and the IsBoss gate keep unrelated spawns safe); if a copy comes through the 4-arg SpawnEnemy(EnemyData, int, bool, EEnemyFlag, bool) overload without forwarding to the positional one, patch that overload too.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 With one Boss Curse active, activating the Warehouse boss portal moves both Lil Barks onto the main half pipe floor at distinct positions, and both can reach and fight the player there
- [x] #2 Killing every summoned boss completes the tier; the curse copies each drop their chest
- [x] #3 A level without bossSpawnPosition and every non-custom-level run behave exactly as before, and only spawns carrying the game's Boss flag are moved
- [x] #4 The arming window, expected-count close and spread clamp live in the Unity-free file with tests written first, and the mod logs every move with both positions
- [x] #5 With bossCurses stacked above 1, each copy lands at a distinct usable position on the floor, none inside the box or below the level
- [x] #6 Verified in the running game with the user driving the shrine and portal interactions
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-11-03 04:16
---
Verified live on fedora with the user driving the Cursed shrine and portal, three consecutive fresh launches of the same build, one curse each (2 bosses). BossSpawnRedirect log: run 1 moved to (163.9, 12.7, 86.6) and (147.3, 20.4, -28.8), 116.5 apart; run 2 to (131.3, 7.6, 17.3) and (170.7, 13.6, 93.0), 85.4 apart; run 3 to (128.1, 7.0, 28.9) and (177.1, 15.7, 68.8), 63.2 apart. All from-spawns were the box-interior lifts near (166-170, 27.5, 26-38); every landing sat on the floor inside the 35-68 band. User confirmed spawns visually usable on all three runs and judged it sufficiently reliable to close. AC #5's multi-curse stack was not run live beyond the 2-boss case; the code path is identical and the multi-taken scoring is unit-tested (PickSpot_ScoresAgainstEveryTakenCopyNotJustTheFirst).

Startup regression observed during verification (harness teleport overwritten by the startup cover, player ending below the level on restart) was filed as TASK-027.02 rather than fixed here.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped: the redirect moves every Boss-flagged spawn the Warehouse portal summons (1 + bossCurses), not just the first. Each boss is teleported to a walkable spot sampled from a random ring around the spawner's XZ at 35-68 units. BossSpawnRedirect.PickSpot scores every usable candidate by its distance to the nearest already-placed copy and keeps the maximum (minimax), so copies spread across the floor instead of landing just over the 20-unit spacing floor; each copy draws its own ring (seed + moveCount * 7919). A spot must pass an all-collider down-ray (highest hit, normal.y > 0.8), sit above killFloorY + 5, keep >= 20 units from other copies, and pass PlacementProbe.ClearPoint; the game's ~11.9-unit spawn lift is preserved so feet land on the surface. SpawnBoss internally calls the positional SpawnEnemy, so both postfixes fire per spawn and a HashSet<IntPtr> of Enemy pointers moves each enemy at most once. The authored bossSpawnPosition is no longer read; it stays in the schema, editor and generator for round-trip stability. Decision logic is Unity-free in boss_spawn_redirect.cs (22 tests, 1741 total C# green); the patch stays thin.

Design departures from the description: the authored anchor was abandoned (anchoring both copies to one point stacked them, and bosses dropped under the box climbed its walls), and drop-to-ground under the spawn failed because LiveEditPatch.GroundCollider() is the generated tile mesh and misses the bundle-placed warehouse mesh (logged 'no ground under the boss'). First-fit candidate selection was replaced with minimax after live runs showed copies 14.7 and 21.2 apart, which still read as stacked.

Live verification (2026-11-02, fedora, user driving shrine and portal), three consecutive runs of the same build, single curse (2 bosses), all landing on the warehouse floor in the 35-68 band: copies 116.5, 85.4 and 63.2 units apart.
<!-- SECTION:FINAL_SUMMARY:END -->
