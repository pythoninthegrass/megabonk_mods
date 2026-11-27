---
id: TASK-086.03.06
title: Recover missing Mountain Pass static mesh material slots
status: To Do
assignee: []
created_date: '2026-11-27 21:46'
labels:
  - kf1
  - level
dependencies:
  - TASK-086.02
references:
  - scripts/kf1_mountain_pass.py
  - tests/test_kf1_mountain_pass.py
documentation:
  - docs/kf1-mountain-pass.md
  - docs/asset-bundles.md
parent_task_id: TASK-086.03
priority: medium
ordinal: 309000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Baseline at 5612816: 308/2,196 static primitives use a fallback, including 212 dummy_material slots, 41 Leaves and 45 Grunge_2_SHDR/Grunge_3_SHDR instances. Trace original StaticMesh sections to package material slots and actor Skins overrides using the original packages, not the placeholder name or visual similarity. Use the export and the static_material lookup; distinguish truly absent or intentionally invisible slots from missing exports.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Regenerating the real map reports counts by mesh, slot and qualified source. Every baseline fallback is resolved or classified with source evidence and documented.
- [ ] #2 Tests cover two actors sharing a mesh with different skin overrides, same-named materials in different packages, and a genuinely empty slot.
- [ ] #3 In-game foliage and representative office/foundry props match the KF1 references; no changes to prop transforms or the player-height calibration.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
