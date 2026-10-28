---
id: TASK-021.17
title: Keep a lifted object's height when dragging it in the editor
status: Done
assignee:
  - '@claude'
created_date: '2026-10-28 05:28'
updated_date: '2026-10-28 05:29'
labels:
  - thps
  - level-editor
dependencies: []
documentation:
  - src/MegabonkLevels.Mod/editor_object_tools.cs
  - src/MegabonkLevels.Mod/object_tool.cs
  - docs/development.md
parent_task_id: TASK-021
priority: medium
ordinal: 105000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Dragging an object in the editor keeps its height above the tile surface (_dragLift in editor_object_tools.cs), so the boss portal, which floats well above the arena floor inside the hanging box, ends up at the new tile surface plus that large lift and lands high above the level when dropped on a raised tile. Chosen fix: when an object is lifted off the surface by more than a threshold, keep its absolute Y while it is dragged sideways; objects standing on the surface keep following it.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Dragging a floating object, such as the boss portal, onto a tile of a different height keeps its Y
- [x] #2 Dragging an object that stands on the surface still follows the surface height
- [x] #3 The Y rule is covered by C# tests written first, and the editor docs describe it
- [x] #4 Checked in game: rotate the boss portal then drag it to another tile and it stays at its height
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added ObjectTools.DragY: an object lifted more than 2 units above the tile surface keeps its absolute Y while dragged, others keep following the surface. Wired into UpdateDrag in editor_object_tools.cs; three C# tests written first; documented in docs/development.md. Checked in game: dragging the boss portal from x=170 to x=82 kept y=15.6. The original sky launch was not reproduced directly (the cause was inferred from the drag code), so the in-game check shows the new behaviour rather than the old bug.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
