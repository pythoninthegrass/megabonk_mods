---
id: TASK-043
title: Log boss spawn and defeat events in the mod
status: To Do
assignee: []
created_date: '2026-11-05 19:46'
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
- [ ] #1 Boss spawn, each boss death and boss defeat each write one log line naming the event and, where available, the count
- [ ] #2 Which events fire for one boss, for a Boss Curse run with several bosses, and for a tier 1 run is recorded in the task, verified in the running game
- [ ] #3 The lines are documented in docs/development.md
- [ ] #4 Subscriptions are removed or guarded so a vanilla run and a level reload do not log duplicates
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
