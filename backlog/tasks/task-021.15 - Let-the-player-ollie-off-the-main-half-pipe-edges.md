---
id: TASK-021.15
title: Let the player ollie off the main half pipe edges
status: To Do
assignee: []
created_date: '2026-10-28 04:12'
labels:
  - thps
  - level-editor
dependencies: []
documentation:
  - docs/thps-warehouse-layout.md
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - tests/test_build_thps_level.py
parent_task_id: TASK-021
priority: high
ordinal: 103000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
At the main half pipe edges near world (142, -3, 32) the player (Tony) cannot ollie off. The edges are too steep: the player stalls on them instead of launching. The earlier suspicion is an engine or movement-logic limit rather than a mesh error. PlayerMovement.maxSlopeAngle is 45 degrees, and docs/thps-warehouse-layout.md ("Pipes stop at 40 degrees") records that a test pipe reaching 56 degrees stalled the player. Since then the pipe became the extracted Warehouse mesh, whose edges are steeper than the old hand-built pipe. Look at the earlier commits that tuned pipe and ramp slopes (for example 50620e0 and a6cda86 and the ramp-slope tests in tests/test_build_thps_level.py), measure the slope at the edges in game, and find whether the limit is the movement code (ground check, slope angle, jump and launch handling) or the collision mesh. The collision mesh is built in unity/pack-authoring/Assets/Editor/ThpsPack.cs. Fix it in the way that is least invasive, such as a mesh edge fix or a level-scoped mod setting.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The cause is identified and written in the task notes, with the measured slope at the edges
- [ ] #2 The player can ride up the main half pipe and ollie off both edges near (142, -3, 32) without stalling
- [ ] #3 The player does not stall or get stuck on the other pipe and ramp edges in the Warehouse
- [ ] #4 The fix does not change movement on the normal Forest levels
- [ ] #5 Any new level-file or mod behaviour is covered by tests and documented in docs/level-format.md or docs/thps-warehouse-layout.md
- [ ] #6 Screenshots or state readings from the run are saved under .tools/evidence/
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
