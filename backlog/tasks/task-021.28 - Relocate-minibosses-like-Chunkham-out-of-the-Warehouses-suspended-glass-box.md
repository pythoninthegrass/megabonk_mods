---
id: TASK-021.28
title: Relocate minibosses like Chunkham out of the Warehouse's suspended glass box
status: To Do
assignee: []
created_date: '2026-11-06 23:09'
updated_date: '2026-11-06 23:09'
labels:
  - bug
  - enemies
  - thps-warehouse
dependencies: []
references:
  - TASK-021.24
  - TASK-021.25
  - TASK-021.26
documentation:
  - docs/development.md
  - docs/thps-warehouse-layout.md
parent_task_id: TASK-021
priority: medium
type: bug
ordinal: 170000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
On the THPS Warehouse level, stage bosses summoned by the boss portal are teleported out of the suspended glass box to a walkable spot in the level interior (TASK-021.25, TASK-021.26). Minibosses do not get the same treatment: a playtester who played a full Windows-package run (beat the boss, infinite ghost wave) reported minibosses such as Chunkham ending up stuck in the suspended glass box, where the player cannot reach or defeat them.

Outcome: minibosses on the Warehouse level end up somewhere reachable instead of stuck in the glass box, using the same relocation behaviour bosses already get. A stuck miniboss should not be able to block or clutter a run.

Context: minibosses come from the game's timeline events (the first, MinibossPig, spawns about 3 minutes into a run), not from the boss portal. See the Boss section of docs/development.md and the miniboss actor classification (`EEnemyFlag.SummonerMiniboss`). Which miniboss types the game can spawn and exactly where each lands in the box is not yet confirmed; the implementer should reproduce it first.

Reproduce: `relaunch levels/thps.mblevel.json` (needs `MEGABONK_DEV=true` and the `thps` pack installed), let the timeline reach a miniboss or trigger one through the harness, and watch where it lands with the dev readout and `query_objects`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Reproduce a miniboss (Chunkham or another type) stuck in the suspended glass box on the Warehouse level and record where it spawned and which miniboss types are affected in docs/development.md
- [ ] #2 Minibosses spawned on the Warehouse level are relocated to a reachable walkable spot in the level interior, away from the glass box, using the same rule bosses use
- [ ] #3 Boss portal bosses and Boss Curse copies keep their current relocation behaviour; the miniboss change does not move unrelated enemies
- [ ] #4 A Python or C# unit test covers the new miniboss relocation rule where it can run without the game
- [ ] #5 Verified in the running game: a miniboss that previously stuck in the glass box now reaches the player, and the result is recorded in docs/development.md
- [ ] #6 docs/development.md describes the miniboss relocation alongside the existing boss spawn redirect
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
