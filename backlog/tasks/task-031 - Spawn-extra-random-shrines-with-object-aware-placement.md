---
id: TASK-031
title: Spawn extra random shrines with object-aware placement
status: To Do
assignee: []
created_date: '2026-11-02T04:32:00Z'
updated_date: '2026-11-02T04:40:00Z'
labels: []
dependencies: []
priority: medium
type: feature
ordinal: 138000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Shrines are the game's core risk-reward choice, but a map spawns a fixed set per seed. Spawning additional shrines at random spots each run adds variety and choice density. The pool includes charge shrines (ChargeShrine, spawned through the dedicated RandomObjectPlacer.chargeShrineSpawns channel rather than MapData.shrines[]), a shrine kind placed nowhere in the Warehouse today, so this also puts one in the run. The constraint is placement awareness: a shrine's interaction trigger is huge (its charge sphere is 12.5 units, per the editor picking notes in docs/development.md), so a badly placed shrine dominates the space around it — it can overlap trees, rocks and chests, or sit right on the routes players run (spawn portal, points of interest, boss portal) and effectively wall off a hot path with a trigger the player keeps bumping. Placement must probe the surface, keep clear of already-spawned objects, and keep the main routes clear. The spot-finding logic can share the placement-probing work of TASK-028 (relocating the shady guy, chests and Maoi) but is deliverable independently.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A configurable number of extra shrines (random types from the map's shrine pool, charge shrines included) spawn each run
- [ ] #2 No extra shrine overlaps an existing spawned object or sits inside another shrine's charge radius
- [ ] #3 No extra shrine obstructs the hot paths: player spawn portal, boss spawner, final portal, and the main routes between them
- [ ] #4 Extra shrines are functional: each can be activated and applies its effect (Challenge, Magnet, Cursed, Greed, Balance, Maoi, Charge)
- [ ] #5 Count and type mix are configurable (level file or mod option), and 0 restores today's behaviour
- [ ] #6 Verified in game on Forest across several seeds: shrines spawn in valid clear spots and none block a main route, including at least one charge shrine spawn
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
