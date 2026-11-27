---
id: TASK-086.03.07
title: Reproduce UE2 surface material behavior in the Unity pack
status: To Do
assignee: []
created_date: '2026-11-27 21:46'
labels:
  - kf1
  - level
dependencies:
  - TASK-086.03.05
  - TASK-086.03.06
references:
  - scripts/kf1_mountain_pass.py
  - tests/test_kf1_mountain_pass.py
documentation:
  - docs/kf1-mountain-pass.md
  - docs/asset-bundles.md
parent_task_id: TASK-086.03
priority: medium
ordinal: 310000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The preview follows Diffuse and guesses cutout from texture alpha. Inspect exported .props.txt and material chains for surfaces actually used by this map. Compare foliage, fence, vehicle/glass, water and emissive examples where present. Distinguish masked opacity from blending and opaque alpha used for specularity. Use KF1-specific material handling; production pack wiring remains TASK-086.04.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Record representative original material chains, opacity inputs, flags and expected behavior, including two-sidedness and animated inputs where used.
- [ ] #2 Synthetic fixtures distinguish opaque alpha, masked and translucent surfaces; exercise nested materials and cyclic or missing inputs without hanging.
- [ ] #3 Build and inspect a Unity 2023.2.22f1 preview: foliage has cutout edges, opaque surfaces do not disappear, and source-backed reflections, emission and UV motion are verified or discrepancies documented.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
