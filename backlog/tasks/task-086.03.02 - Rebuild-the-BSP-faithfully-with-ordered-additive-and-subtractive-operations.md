---
id: TASK-086.03.02
title: Rebuild the BSP faithfully with ordered additive and subtractive operations
status: To Do
assignee: []
created_date: '2026-11-27 18:27'
labels:
  - level
  - kf1
dependencies:
  - TASK-086.03.01
documentation:
  - docs/kf1-mountain-pass.md
parent_task_id: TASK-086.03
priority: low
ordinal: 305000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Second, faithful version of the BSP: apply the additive and subtractive `Brush` actors in level order (the order they appear in the exported T3D) with a mesh boolean library, so rooms and doorways carved by subtractive brushes are reproduced and hidden interior faces are removed. Replaces the approximate geometry from the first subtask once it is correct; compare the two in the running game and keep the approximate result if the boolean output is unreliable on any brush. Check the result is watertight enough for the collision mesh and does not slow level load noticeably.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Subtractive brushes carve the additive geometry in level order, and unit tests cover a carved box and a doorway
- [ ] #2 Interior faces hidden by the boolean operations are removed from the render mesh
- [ ] #3 A before-and-after screenshot of a building interior from the running game shows the difference from the approximate version
- [ ] #4 Load time and collision behavior are checked and any brush that fails falls back to the approximate geometry
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
