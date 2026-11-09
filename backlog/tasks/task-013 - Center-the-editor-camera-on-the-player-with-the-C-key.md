---
id: TASK-013
title: Center the editor camera on the player with the C key
status: Done
assignee:
  - pythoninthegrass
created_date: '2026-10-23T16:51:00Z'
updated_date: '2026-10-23T17:40:00Z'
labels:
  - editor
dependencies: []
type: feature
ordinal: 64000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In editor mode the free-fly camera can end up far from the player, and the player is easy to lose track of on a large level. A single key that snaps the camera back to the player lets the user recover focus from anywhere.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Pressing C in editor mode moves the free-fly camera to the player's position from anywhere on the level
- [x] #2 C does nothing outside editor mode
- [x] #3 C does not fire while a text field in the editor has input focus
- [x] #4 C does not conflict with an existing editor key binding
- [x] #5 A test covers the camera-target calculation, and the key is listed in the editor key documentation
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. In `EditorMode.Fly` (editor_mode.cs), on C key-down while no text field has focus and Ctrl is not held, reset `_pose` to `FreeFlyCamera.OverviewPose` at `MyPlayer.Instance.transform.position` (the same pose editor entry uses).
2. Add a `CenterKey` constant beside `ToggleKey`; no new pure logic, so the camera-target maths stays covered by the existing `OverviewPose` test in free_fly_camera_tests.cs.
3. Document the key in the editor mode section of docs/development.md.
4. Verify in the running game via the megabonk MCP server: fly away, press C, screenshot, confirm the player is centred; confirm C is inert outside editor mode.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
C verified in the running game after relaunch: camera snaps to the overview pose over the player. 658 xUnit tests pass. AC 2 and 3 rest on code: Fly only runs while the session is active, and the key uses the same TextInputFocused guard as the movement keys; neither was exercised in game. No new pure logic, so no new test; OverviewPose is covered by free_fly_camera_tests.cs.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Pressing C in editor mode resets the free-fly camera to the overview pose over the player, so the camera can recover from anywhere on the level. The key is ignored while a text field has focus or Ctrl is held. Added to the key table in docs/development.md. Verified in game by the user; unit tests pass. AC 2 and 3 were not exercised in game.
<!-- SECTION:FINAL_SUMMARY:END -->
