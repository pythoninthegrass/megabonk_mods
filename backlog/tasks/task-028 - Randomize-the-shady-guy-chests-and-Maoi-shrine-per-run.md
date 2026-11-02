---
id: TASK-028
title: 'Randomize the shady guy, chests and Maoi shrine per run'
status: To Do
assignee: []
created_date: '2026-11-02T04:32:00Z'
labels: []
dependencies: []
priority: medium
type: feature
ordinal: 135000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In stock Megabonk the interactables that matter run to run land at fixed spots for a given seed: the shady guy merchant (InteractableShadyGuy; the catalog's ShadyGuy prefab), chests (InteractableChest) and the stone-head Maoi shrine (InteractableShrineMoai). The mod's seed-determinism work (docs/map-generation-determinism.md) pins every spawn phase, so a level replays identically every run — an author who wants replay variety gets none: same shopping trip, same chest spots, same Maoi, every time. Let a level re-roll where these specific interactables spawn on each run while the rest of the world stays deterministic.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 With randomization enabled, two runs of the same level file and seed place the shady guy, chests and Maoi at different spots
- [ ] #2 Randomized placements stay valid: on the ground surface, upright, reachable, and not overlapping other spawned objects
- [ ] #3 With randomization off (default), placement is unchanged and the seed-determinism guarantee from map-generation-determinism.md still holds
- [ ] #4 Randomization can be toggled per object kind, e.g. randomize chests while pinning the shady guy
- [ ] #5 Verified in game on Forest: consecutive runs show different spots, and turning it off restores today's placement exactly
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
