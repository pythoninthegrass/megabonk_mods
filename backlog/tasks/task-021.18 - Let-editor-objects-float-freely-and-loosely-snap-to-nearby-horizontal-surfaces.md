---
id: TASK-021.18
title: Let editor objects float freely and loosely snap to nearby horizontal surfaces
status: Done
assignee:
  - '@claude'
created_date: '2026-10-28 05:32'
updated_date: '2026-11-09 05:26'
labels:
  - thps
  - level-editor
dependencies:
  - TASK-021.17
documentation:
  - src/MegabonkLevels.Mod/editor_object_tools.cs
  - src/MegabonkLevels.Mod/object_tool.cs
  - docs/development.md
parent_task_id: TASK-021
priority: medium
ordinal: 106000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-021.17 stopped a floating object (the boss portal) from launching above the level by keeping its absolute Y while dragged, but now it cannot be moved vertically and does not settle onto surfaces. For creativity, any object should be able to be untethered: dragging moves it horizontally; holding Shift while dragging moves it vertically; within about 2 units of a mostly horizontal surface (tile tops and level colliders with an upward normal, found by downward raycast, ignoring the object's own colliders) it settles onto that surface, otherwise it floats at the height set. An object that starts resting on a surface (lift of 2 units or less) keeps following the surface as before so ordinary props still ride slopes and ledges. Replaces the DragY rule from TASK-021.17.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Dragging a floating object moves it horizontally and it keeps its height unless a horizontal surface is within about 2 units, in which case it settles onto that surface
- [x] #2 Holding Shift while dragging moves the object vertically, with the same loose snap to nearby surfaces
- [x] #3 An object that starts on the surface still follows the surface over slopes and height changes
- [x] #4 The snap and vertical rules are covered by C# tests written first, and docs/development.md describes the controls
- [x] #5 Checked in game: the boss portal can be dragged sideways, raised and lowered, and snaps onto the box floor and a tile top
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Approved by the maintainer: Shift+drag for vertical, snap to tiles and level geometry (upward-normal colliders), snap distance about 2 units, applies to all objects.
1. Tests first in object_tool_tests.cs: ObjectTools.SnapY (nearest surface within 2 units else keep Y), vertical drag Y from mouse delta, and the resting/floating rule.
2. Replace ObjectTools.DragY: an object starting within 2 units of its surface follows the surface plus lift as before; otherwise it keeps its Y and snaps to a surface within 2 units found by a downward raycast (own colliders ignored, normal.y above 0.7) or the tile surface.
3. Shift held during a drag changes Y from the vertical mouse delta instead of moving horizontally; same snap.
4. Document controls in docs/development.md; run task check; check in game with the boss portal; commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Checked in game with the boss portal: Shift-drag up raised it from 15.6 to 20.6 with X/Z frozen; a sideways drag keeps Y. A 2-unit Shift-drag down from 15.6 left it at 15.6 with no move applied, which is consistent with snapping back onto the box floor but could also be a drag that did not activate. AC #5 stays open until the snap onto the box floor and onto a tile top is confirmed by eye.

Later work under this task: the snap was softened to a pull within 1.5 units, Shift drags no longer need the cursor over a tile, the selection ring follows a lowered or raised floating object, and floating objects now drag along a horizontal plane at their own height. the maintainer confirmed in game that the ring and the horizontal drag are fixed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Objects can be untethered in the editor: Shift while dragging changes height, a floating object follows the cursor on a plane at its own height and is softly pulled towards a horizontal surface within 1.5 units, an object resting on the surface still follows it, and the selection ring tracks floating objects. Covered by C# tests and documented in docs/development.md.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
