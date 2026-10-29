---
id: TASK-021.22
title: End a grind before a wall with a StopRail patch
status: To Do
assignee: []
created_date: '2026-10-29 03:41'
labels:
  - thps
  - mod
dependencies:
  - TASK-021.21
documentation:
  - docs/thps-warehouse-layout.md
  - src/MegabonkLevels.Mod/rail_handoff_patch.cs
parent_task_id: TASK-021
priority: medium
ordinal: 113000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A grind that runs off the end of a rail launches the player along the rail's tangent. On the Warehouse coping rails (TASK-021.21), a lip that ends at a wall launches the player into it and the skater bails; the report was near (178, 7, 46), the east end of the main half pipe's south lip. Shortening the rail (WALL_ENDS and WALL_MARGIN in scripts/build_thps_level.py) does not fix it: the player coasts along the flat lip into the wall anyway.

The outcome is that a grind detaches from the lip with room to spare before a wall, instead of ending in a collision. Context for a fresh implementer: RailHandoffPatch (src/MegabonkLevels.Mod/rail_handoff_patch.cs) already postfixes PlayerMovement.StopRail on custom levels to hand a grind to the next rail. Extending that patch, or adding a sibling, to end the grind early when a wall lies ahead along the rail tangent is the likely route. docs/thps-warehouse-layout.md ("Coping rails on the half pipes and wall quarter pipes") records the wall ends found by probing the mesh and the harness limit: a harness drop only grinds west, so an eastbound grind needs a manual test.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Grinding a coping rail toward a wall ends the grind before the player reaches the wall, with no bail, at the east end of the main half pipe lips near (178, 7, 46) and the wall ends listed in WALL_ENDS
- [ ] #2 Grinds that do not run toward a wall are unchanged, including the handoff between chained rails
- [ ] #3 The detach distance and wall detection are covered by tests, written first, and the behaviour is documented in docs/thps-warehouse-layout.md and level-format.md where it applies
- [ ] #4 Checked in game with an eastbound grind into the east wall
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
