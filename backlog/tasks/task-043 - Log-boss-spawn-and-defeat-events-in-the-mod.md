---
id: TASK-043
title: Log boss spawn and defeat events in the mod
status: Done
assignee: []
created_date: '2026-11-05 19:46'
updated_date: '2026-11-05T20:19:00Z'
labels:
  - logging
  - harness
dependencies: []
references:
  - >-
    backlog/tasks/task-032.06 -
    Port-the-THPS-Warehouse-to-a-from-scratch-level.md
  - src/MegabonkLevels.Mod/boss_spawn_redirect_patch.cs
priority: high
ordinal: 163000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
After a boss fight on the Warehouse (TASK-032.06) the mod log showed the boss redirect but nothing after it: no boss death and no defeat event, so a boss kill could only be confirmed by the player. The game raises static events for this in dump.cs: A_BossSpawned, A_BossDefeated(bool), A_NumBossesDefeated(int), A_BossDied and A_StageBossDied (find the owning classes with rg -u in .tools/il2cpp_dump/dump.cs).

Subscribe to the relevant events and write one log line each (spawn, each boss death, defeat with the count), in the style of the BossSpawnRedirect lines, so log_wait can match them. Check which events fire for a single boss, for a Boss Curse run with several bosses, and on a tier 1 run where waves continue after the kill. Logging only: no gameplay change. Document the lines in docs/development.md next to "Boss spawn redirect".
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Boss spawn, each boss death and boss defeat each write one log line naming the event and, where available, the count
- [x] #2 Which events fire for one boss, for a Boss Curse run with several bosses, and for a tier 1 run is recorded in the task, verified in the running game
- [x] #3 The lines are documented in docs/development.md
- [x] #4 Subscriptions are removed or guarded so a vanilla run and a level reload do not log duplicates
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
1. Owners (dump.cs): InteractableBossSpawner holds A_BossSpawned, A_BossDefeated(bool), A_NumBossesDefeated(int); GraveyardBossRoom holds A_BossDied; EnemyManager holds A_StageBossDied. FinalFightController has its own A_BossDefeated/A_BossDefeatedTime, out of scope.
2. TDD: Unity-free `BossEventLog.Format` (boss_event_log.cs) builds the line `BossEvents: <event>[ <value>]`; xunit tests first, linked into the test csproj.
3. `BossEventPatch.Install` (boss_event_patch.cs) subscribes once from OnInitializeMelon with `(Il2CppSystem.Action)` delegates, like GenerationPatch. One subscription per process means a level reload or vanilla run cannot log duplicates (AC4).
4. Build, relaunch, and observe in the running game: one boss, Boss Curse with several bosses, tier 1 run. Record which events fire in the task notes (AC2).
5. Document the lines in docs/development.md under "Boss spawn redirect"; run task check; commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented: boss_event_log.cs (tested), boss_event_patch.cs, wired in OnInitializeMelon. Warehouse run (levels/thps.mblevel.json), player given BossBuster/GymSauce/BrassKnuckles to kill bosses.

One boss: A_BossSpawned, then A_StageBossDied, A_BossDefeated False, A_NumBossesDefeated 1 (all within 10 ms of the kill). A_BossDied (GraveyardBossRoom) did not fire, as expected off the graveyard map.

Boss Curse, 1 curse (2 bosses summoned, redirect expected 2 and moved 2): A_BossSpawned fired once, not per boss. After the kill, A_StageBossDied once, A_BossDefeated False once, A_NumBossesDefeated 3 (the counter is cumulative and jumped 1 -> 3, i.e. +2 for the two curse bosses). It is not confirmed that both bosses had died by then.

Tier 1 run (relaunch --tier 1, spawns left on): A_BossSpawned, A_StageBossDied, A_BossDefeated True; A_NumBossesDefeated did not fire in 100 s after the kill. Spawns stayed on, so waves continue after the kill. Observed: the bool is False on the tier 0 runs above and True on tier 1, so it appears to mean 'the run's waves continue/the stage keeps going'; its meaning is inferred from two data points, not confirmed in code.

AC4: subscriptions are made once in OnInitializeMelon; each event logged exactly one line per occurrence across two spawns in one process. A `load` into a running game was not tried (the harness advises against it).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added BossEventPatch (boss_event_patch.cs) and BossEventLog (boss_event_log.cs, unit tested). The mod subscribes once at startup to A_BossSpawned, A_BossDefeated(bool) and A_NumBossesDefeated(int) on InteractableBossSpawner, A_BossDied on GraveyardBossRoom and A_StageBossDied on EnemyManager, and writes one `BossEvents: <event> [value]` line each. Verified on the Warehouse: one boss, a Boss Curse summon of two bosses, and a tier 1 run; the observed firing is recorded in the notes and in docs/development.md ("Boss event log lines"). Caveats: A_BossDied only fires in the graveyard boss room; the meaning of the A_BossDefeated bool is inferred; the curse run logged one A_StageBossDied for two bosses and the counter went 1 -> 3; a load into a running game was not tried for AC4, which rests on the single startup subscription.
<!-- SECTION:FINAL_SUMMARY:END -->
