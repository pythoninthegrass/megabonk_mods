---
id: TASK-021.26
title: >-
  Move every Boss Curse copy to the authored boss spawn position, not just the
  first
status: To Do
assignee: []
created_date: '2026-11-02T04:15:00Z'
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
  - tests/MegabonkLevels.Tests/boss_spawn_redirect_tests.cs
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
- [ ] #1 With one Boss Curse active, activating the Warehouse boss portal moves both Lil Barks onto the main half pipe floor at distinct positions, and both can reach and fight the player there
- [ ] #2 Killing every summoned boss completes the tier; the curse copies each drop their chest
- [ ] #3 A level without bossSpawnPosition and every non-custom-level run behave exactly as before, and only spawns carrying the game's Boss flag are moved
- [ ] #4 The arming window, expected-count close and spread clamp live in the Unity-free file with tests written first, and the mod logs every move with both positions
- [ ] #5 With bossCurses stacked above 1, each copy lands at a distinct usable position on the floor, none inside the box or below the level
- [ ] #6 Verified in the running game with the user driving the shrine and portal interactions
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
