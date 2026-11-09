---
id: TASK-005.09
title: Object rotation on all three axes in the editor
status: Done
assignee:
  - claude
created_date: '2026-10-10 07:39'
updated_date: '2026-11-09 05:26'
labels:
  - level-editor
dependencies:
  - TASK-005.04
parent_task_id: TASK-005
priority: medium
ordinal: 50000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The editor's Select tool (TASK-005.04) rotates a selected object only about the vertical axis, in 90 degree yaw steps (R clockwise, Shift+R counter-clockwise), keeping the object's pitch and roll. the maintainer wants objects to be rotatable in 3D as well, so an object can be tilted, laid on its side or turned upside down, not only turned to face a different compass direction. The level format's MoveObject op already carries a full rotation (X, Y, Z), so the limit is the editor input and its rules, not the saved data. Context: tools and input are described under "Object tools" in docs/development.md; the pure rules are in src/MegabonkLevels.Mod/object_tool.cs (ObjectTools.Rotate) with tests in tests/MegabonkLevels.Tests/object_tool_tests.cs. Which keys or gestures drive the extra axes, and the step size per axis, are open and need the maintainer's decision before work starts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A selected object can be rotated about each of the three axes from the editor, generated and editor-placed objects alike
- [x] #2 Each rotation produces a MoveObject with the full resulting rotation and the object's position and scale unchanged, applied live through the EditStack
- [x] #3 The rotation survives a save and reload of the level file
- [x] #4 Existing yaw rotation (R and Shift+R) keeps working
- [x] #5 The key bindings do not trigger a game action and do not clash with the digit tool hotkeys, the free-fly camera or Delete and Backspace (checked in game)
- [x] #6 Rotation rules have tests written first, and docs/development.md describes the controls
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Keys (the maintainer's decision): R/Shift+R yaw (unchanged), F/Shift+F pitch about world X, G/Shift+G roll about world Z; 90 degree steps composed in world space.
1. Tests first in object_tool_tests.cs for ObjectTools.Rotate(target, current, RotationAxis, positive).
2. Implement RotationAxis and the Unity ZXY euler matrix compose in object_tool.cs; yaw keeps its direct Y edit.
3. Bind F and G in editor_object_tools.cs HandleSelectionKeys.
4. Document in docs/development.md Object tools table.
5. Verify in game through the megabonk MCP.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
In game (CrossOver): selected ChargeShrine:0007, F then G each logged object.move and the shrine visibly tipped onto its side; save wrote two object.move ops with full rotation (296.842,270,270 then 26.842,270,270), position and scale unchanged. Not yet done: Load of the saved file to confirm the rotation after reload (AC3), and a check that F/G do nothing in normal play (AC5). Euler results are Unity-canonical (pitch limited to 0-90 / 270-360), so an upside-down object saves as 0,180,180.

Reload verified in game: rotated ChargeShrine:0007 with F and Shift+G, saved as rotcheck, pressed Load; log showed 'LiveEdit: in-place load applied 2 edit(s) after baseline reset' and the shrine stayed tilted. AC5 left open: the harness injects into EditorInput only and cannot reach the game's Rewired input, so whether the game binds F or G needs a real keypress in the running game.

the maintainer confirmed in the running game that F and G trigger no game action.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Selected objects now rotate about all three axes in the editor: R / Shift+R yaw (unchanged), F / Shift+F pitch about world X, G / Shift+G roll about world Z, 90 degrees per press. ObjectTools.Rotate takes a RotationAxis; pitch and roll compose in world space using Unity's ZXY euler order and are written back as euler angles (canonical form, so an upside-down object saves as 0,180,180). Each press is one MoveObject with the full rotation and position and scale unchanged. Verified: task check passes (tests written first), in-game rotation of a generated shrine, save wrote the full rotation, and Load replayed the 2 edits with the shrine still tilted; F and G confirmed by the maintainer to do nothing in the game. Editor-placed objects were not exercised separately (same code path).
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
