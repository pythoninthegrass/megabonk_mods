---
id: TASK-021.21
title: Grind the apex edges of the half pipes like the rails
status: To Do
assignee: []
created_date: '2026-10-28T21:02:00Z'
labels:
  - thps
  - level-editor
dependencies:
  - TASK-021.19
  - TASK-021.15
documentation:
  - docs/thps-warehouse-layout.md
  - scripts/build_thps_level.py
parent_task_id: TASK-021
priority: medium
type: feature
ordinal: 111000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Make the apex edge (coping) of every half pipe and quarter pipe in the Warehouse grindable, the same way the three mesh rails are.

Context for a fresh implementer: apply the hidden game rail approach from TASK-021.14 and TASK-021.19. Rails are laid along the visible geometry with MESH_RAILS in scripts/build_thps_level.py, placed with the hidden flag on object.place; the pivot height offset scales with the rail (RAIL0_BAR_HEIGHT); RailHandoffPatch (rail_handoff_patch.cs) chains rails that meet at a joint. Measure each lip line from the extracted mesh. The main half pipe near (142, -3, 32) must keep working for ollies (TASK-021.15, PlayerMovement.maxSlopeAngle raised to 88 on the thps level).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every half pipe and quarter pipe lip has a hidden game rail aligned to the coping, with each pipe and its coordinates listed in the task
- [ ] #2 The player can grind each lip in game, with the grind sparks and player on the visible edge
- [ ] #3 Ollie off the main half pipe edges near (142, -3, 32) still works
- [ ] #4 Generator behaviour is covered by tests in tests/test_build_thps_level.py written first, and docs/thps-warehouse-layout.md is updated
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
