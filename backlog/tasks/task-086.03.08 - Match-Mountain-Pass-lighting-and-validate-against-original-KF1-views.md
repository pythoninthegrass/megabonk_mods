---
id: TASK-086.03.08
title: Match Mountain Pass lighting and validate against original KF1 views
status: To Do
assignee: []
created_date: '2026-11-27 21:46'
labels:
  - kf1
  - level
dependencies:
  - TASK-086.03.04
  - TASK-086.03.07
references:
  - scripts/kf1_mountain_pass.py
  - tests/test_kf1_mountain_pass.py
documentation:
  - docs/kf1-mountain-pass.md
  - docs/asset-bundles.md
parent_task_id: TASK-086.03
priority: medium
ordinal: 311000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Use the original KF-MountainPass_Day in KF1 or its SDK for reference. KF2 footage is a layout aid, not a palette target. Capture road/bridge, hillside and an accessible interior with identifiable landmarks; record camera position, orientation and reference conditions. Compare sky, fog, ambient/directional light and baked shading separately from material color. The unlit preview is the baseline. Do not make this wait for faithful BSP or release packaging; use an accessible room and record geometric occlusion separately.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A local matched-view set identifies each landmark and separates diffuse/UV errors from lighting, fog and geometry differences.
- [ ] #2 The preview reproduces verified KF1 sky, fog and light settings or documents per-setting limitations with evidence; lighting corrections do not recolor Tony, the HUD or other maps.
- [ ] #3 Document reproducible build, relaunch and screenshot steps, and outstanding differences by view. Commit no ripped assets, packages or screenshots.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
