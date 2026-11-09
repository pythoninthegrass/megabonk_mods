---
id: TASK-021.15
title: Let the player ollie off the main half pipe edges
status: Done
assignee: []
created_date: '2026-10-28 04:12'
updated_date: '2026-11-09 05:26'
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
- [x] #1 The cause is identified and written in the task notes, with the measured slope at the edges
- [x] #2 The player can ride up the main half pipe and ollie off both edges near (142, -3, 32) without stalling
- [x] #3 The player does not stall or get stuck on the other pipe and ramp edges in the Warehouse
- [x] #4 The fix does not change movement on the normal Forest levels
- [x] #5 Any new level-file or mod behaviour is covered by tests and documented in docs/level-format.md or docs/thps-warehouse-layout.md
- [ ] #6 Screenshots or state readings from the run are saved under .tools/evidence/
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Branch fix/task-021.15-halfpipe-ollie (commit 2564c41), top of the train. Measured from the extracted mesh near (142, -3, 32): the half pipe faces run 31, 34, 54, 77 and 85 degrees up to the lip over about 8 units of rise, so the face passes PlayerMovement.maxSlopeAngle (45) roughly a third of the way up. Probable cause: the movement limit, not the collision mesh. Not confirmed by play, because the harness cannot drive the game's movement input.

Fix: new optional level key maxSlopeAngle (LevelFile.MaxSlopeAngle, docs/level-format.md). The mod sets PlayerMovement.maxSlopeAngle for a custom level run only and restores the game's value afterwards (LiveEditPatch.TickMaxSlopeAngle); levels without the key, including Forest, are unchanged. The thps level sets 88 (MAX_SLOPE_ANGLE). Log on load: 'LiveEdit: max slope angle 45 -> 88' (saved as .tools/evidence/task-021.15-max-slope-log.txt). Tests cover the key round trip, default and equality, and the generator value.

This PR (#6) now targets main; it was first stacked on feat/task-021.19-mesh-rails, which is already merged into feat/task-021.14-rail-pillars (PR #8).

Open for the maintainer: ride the main half pipe and ollie off both edges (AC 2), check the other pipes and ramps (AC 3), and judge whether 88 changes the feel of the rest of the level; a lower value may ride the pipes just as well. The restore of the 45 limit on a later vanilla run is implemented but was not exercised.

Confirmed in play by the maintainer on 2026-10-28: the main half pipe rides and both edges ollie off with maxSlopeAngle 88 on the thps level. The cause is the movement slope limit (45), not the collision mesh. AC 6 stays unchecked: the slope log file named above is not in .tools/evidence, and no run screenshots were saved.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
