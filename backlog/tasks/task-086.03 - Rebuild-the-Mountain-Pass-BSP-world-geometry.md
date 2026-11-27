---
id: TASK-086.03
title: Rebuild the Mountain Pass BSP world geometry
status: To Do
assignee: []
created_date: '2026-11-27 08:20'
updated_date: '2026-11-27 19:47'
labels:
  - level
  - kf1
dependencies:
  - TASK-086.02
references:
  - TASK-086.05
documentation:
  - docs/kf1-mountain-pass.md
parent_task_id: TASK-086
priority: medium
ordinal: 302000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The level's BSP is not in the exported data as a mesh: the T3D holds 462 `Brush` actors (432 with geometry, none rotated; vertices are brush-local, so world position is vertex minus `PrePivot` plus `Location`). 337 are additive (2,053 polygons, mostly walls, ledges and stairs with building, road and tunnel textures) and 94 are subtractive (566 polygons, the largest being the world void). 29 additive brushes use `Engine.BlackTexture` and include the largest volumes; their purpose (invisible collision or zone filler) is not established. This task rebuilds the geometry in two steps, approximate first and faithful second, so the level is playable after the first. See docs/kf1-mountain-pass.md for the measurements.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The additive brush geometry is part of the level mesh and collision, built by the subtasks below
- [ ] #2 What the BlackTexture brushes are is established and written down in docs/kf1-mountain-pass.md
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
From TASK-086.02: anchors on BSP floors have no terrain floor and are skipped: 17/157 ZombieVolume, 3/4 ShopVolume, 4/14 KFAmmoPickup, 6/14 KFRandomItemSpawn. The level has one shrine spot and the runtime needs more spots than shrines, so shrine spots need adding once the BSP gives those anchors a floor (converter: scripts/kf1_mountain_pass.py, make_level).
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
