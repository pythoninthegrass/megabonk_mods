---
id: TASK-086.03.04
title: Blend and align Mountain Pass terrain layers
status: To Do
assignee: []
created_date: '2026-11-27 21:46'
labels:
  - kf1
  - level
dependencies:
  - TASK-086.03.03
references:
  - scripts/kf1_mountain_pass.py
  - tests/test_kf1_mountain_pass.py
documentation:
  - docs/kf1-mountain-pass.md
  - docs/asset-bundles.md
parent_task_id: TASK-086.03
priority: high
ordinal: 307000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Consume the preceding layer inventory. terrain_primitive currently emits solid vertex color and no UVs. Use the layer masks in source order and the UE2 texture transforms, not a height or slope classifier. Preserve the existing 256×256 height samples, indexing, collision and 0.0385 scale. Extend the KF1 preview import as needed; do not wait on the release packaging task. Keep maps, baked textures and screenshots local.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A small asymmetric fixture verifies row/column orientation, a 50% blend, overlapping masks in slot order and different U/V repeat rates.
- [ ] #2 prepare produces terrain material data loadable by the Unity preview; terrain vertices, collision indices and grounded anchors match the pre-texture baseline.
- [ ] #3 Matched original KF1 and Megabonk views of the road shoulder and hillside show corresponding grass, dirt, rock and gravel boundaries and tiling; record poses and local evidence paths.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
