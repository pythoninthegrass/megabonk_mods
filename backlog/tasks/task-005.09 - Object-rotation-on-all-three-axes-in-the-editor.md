---
id: TASK-005.09
title: Object rotation on all three axes in the editor
status: To Do
assignee: []
created_date: '2026-10-10 07:39'
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
The editor's Select tool (TASK-005.04) rotates a selected object only about the vertical axis, in 90 degree yaw steps (R clockwise, Shift+R counter-clockwise), keeping the object's pitch and roll. Lance wants objects to be rotatable in 3D as well, so an object can be tilted, laid on its side or turned upside down, not only turned to face a different compass direction. The level format's MoveObject op already carries a full rotation (X, Y, Z), so the limit is the editor input and its rules, not the saved data. Context: tools and input are described under "Object tools" in docs/development.md; the pure rules are in src/MegabonkLevels.Mod/object_tool.cs (ObjectTools.Rotate) with tests in tests/MegabonkLevels.Tests/object_tool_tests.cs. Which keys or gestures drive the extra axes, and the step size per axis, are open and need Lance's decision before work starts.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A selected object can be rotated about each of the three axes from the editor, generated and editor-placed objects alike
- [ ] #2 Each rotation produces a MoveObject with the full resulting rotation and the object's position and scale unchanged, applied live through the EditStack
- [ ] #3 The rotation survives a save and reload of the level file
- [ ] #4 Existing yaw rotation (R and Shift+R) keeps working
- [ ] #5 The key bindings do not trigger a game action and do not clash with the digit tool hotkeys, the free-fly camera or Delete and Backspace (checked in game)
- [ ] #6 Rotation rules have tests written first, and docs/development.md describes the controls
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
