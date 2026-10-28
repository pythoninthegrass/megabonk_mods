---
id: TASK-021.19
title: >-
  Make the other two mesh rails grindable and remove the stray mesh artifacts at
  all three
status: To Do
assignee: []
created_date: '2026-10-28 06:08'
labels:
  - thps
  - level-editor
dependencies:
  - TASK-021.14
documentation:
  - docs/thps-warehouse-layout.md
  - scripts/build_thps_level.py
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - docs/level-format.md
parent_task_id: TASK-021
priority: medium
ordinal: 107000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Warehouse mesh has three rails. The first, near world (81, 3, 27), was made grindable in TASK-021.14 by laying hidden game rails along the mesh bar (MESH_RAILS in scripts/build_thps_level.py, placed with the hidden flag on object.place) and adding pillars in ThpsPack.cs (AddRailPosts). Apply the same treatment to the other two, near (127, 22, 123) and (178, 8, 62), so all three match: a hidden game rail aligned to each mesh bar, and pillars where the first rail has them. All three rails also have stray mesh artifacts floating near each pillar; find what they are (leftover geometry from the extracted Warehouse mesh, or from the pillars) and clean them up on all three rails.

Positions are approximate. Measure each bar from top-down and side screenshots as in TASK-021.14 (evidence under .tools/evidence/, for example rail_align_top2.png). Grind activation on the first rail is a separate open question in TASK-021.14 and is not part of this task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The rails near (127, 22, 123) and (178, 8, 62) each have a hidden game rail aligned to the mesh bar, set up the same way as the rail near (81, 3, 27)
- [ ] #2 Pillars match the first rail's pillars on the other two rails
- [ ] #3 The stray floating mesh artifacts near the pillars are gone on all three rails, with before and after screenshots saved under .tools/evidence/ and noted in the task
- [ ] #4 The player can grind each of the three rails (checked in game, noting how the grind was checked)
- [ ] #5 Any new generator or pack behaviour is covered by tests in tests/test_build_thps_level.py, and docs/thps-warehouse-layout.md is updated
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
