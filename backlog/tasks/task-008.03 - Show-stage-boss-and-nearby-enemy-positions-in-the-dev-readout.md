---
id: TASK-008.03
title: Show stage boss and nearby enemy positions in the dev readout
status: In Progress
assignee: []
created_date: '2026-10-08 05:14'
updated_date: '2026-10-08 06:14'
labels:
  - level-editor
dependencies:
  - TASK-008.02
parent_task_id: TASK-008
priority: medium
ordinal: 45000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the dev-only on-screen readout from TASK-008.02 (player world position, grid cell and kill-floor height, drawn only when the dev harness is enabled) with positions of the stage boss and enemies. This was wanted after a manual playthrough where enemies were killed by the kill floor in large numbers and the Forest stage boss (Lil Bark) left the map through a removed-tile hole alive with its health bar still up, and the log gave no position to see where either went. The kill-floor watcher (src/MegabonkLevels.Mod/kill_floor_watcher.cs) iterates EnemyManager.enemies (Dictionary<uint, Enemy>); EnemyManager also keeps a private stageBosses list, and the boss did not show up in the watcher's log, so how to enumerate the boss reliably is part of this task. Cell coordinates follow the live map layout: cell (x, z) is at world (-280 + 40x, 20 * height, -280 + 40z) on the 15x15 Forest map, with spacing from StageData.mapParameters at runtime. A run has hundreds of enemies, so the readout must stay readable: show the boss and a small number of enemies chosen by a rule, not every enemy. Out of scope: changing what the kill floor kills (that is tracked in the kill-floor work) and the game's own minimap.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The readout shows the stage boss's world position, grid cell and whether it is below the kill floor, in a level where a stage boss exists, and shows nothing for it otherwise
- [ ] #2 The readout lists a bounded number of enemies chosen by a documented rule (for example nearest to the player plus any below the kill floor), each with world position and grid cell, and the on-screen text stays readable with hundreds of live enemies
- [x] #3 The selection rule (which enemies to show, in what order, capped at how many) is pure logic with unit tests written before the implementation
- [ ] #4 The readout adds no per-frame allocation or cost that is noticeable in the running game with a full wave of enemies
- [ ] #5 Verified in the running game with a screenshot that shows the boss and enemy lines, and the boss line matches the boss's observed position
- [ ] #6 docs/development.md documents the added lines and the selection rule
<!-- AC:END -->



## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
