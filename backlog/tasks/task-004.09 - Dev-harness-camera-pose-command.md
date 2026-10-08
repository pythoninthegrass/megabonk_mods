---
id: TASK-004.09
title: 'Dev harness: camera pose command'
status: Done
assignee:
  - Claude
created_date: '2026-10-08 03:41'
updated_date: '2026-10-08 03:51'
labels:
  - level-editor
dependencies:
  - TASK-004.06
  - TASK-004.08
parent_task_id: TASK-004
priority: medium
ordinal: 40000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the dev harness (TASK-004.06; docs/development.md) with a camera command so a screenshot can show a chosen view, for example an overhead shot of edited tiles, instead of the spawn portal. Runs after TASK-004.08 (freeze) so the scene holds still while the camera is posed.

`PlayerCamera.Instance` (public `Camera camera`, private `cameraState`) recomputes its pose from the player's head position and look rotation every `Update`, so a plain `transform` write is overwritten the next frame. Approach: the mod stores the requested pose and re-applies it after the game's update, from MelonLoader's `OnLateUpdate` (preferred, because it avoids a Harmony patch on an Il2Cpp method) or a postfix on `PlayerCamera.Update`. The existing end-of-frame `Texture2D.ReadPixels` screenshot then captures that pose. Confirm in the running game that nothing later in the frame (`CameraOutlines`, the shaker) moves the camera back.

Cell (x, z) is at world (-280 + 40x, 20 * height, -280 + 40z) on Forest, read from `MapParameters.scaledTileWidth` and `scaledTileHeight` at runtime. Camera control only helps screenshots; the enemy playthrough in TASK-004.03 / TASK-004.05 still needs a surviving player.

Related: TASK-005.01 needs a free-fly camera for the in-game editor. Settle whether this override and that one share an implementation before building either.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A harness command sets the camera position and euler rotation, and a matching command clears the override and returns control to the game, with each logged
- [x] #2 A screenshot taken after the command shows the requested view, not the game's own pose, verified on an edited Forest level
- [x] #3 The pose survives the game's own camera update for the whole settle period
- [x] #4 `run.py camera` and `run.py camera --clear` subcommands exist, and `cycle` accepts a camera pose flag
- [x] #5 Pure command parsing for the new command is unit tested, with the tests written before the implementation
- [x] #6 The command, its coordinate convention, and any caveats are documented in docs/development.md
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first: C# harness_command_tests for camera (position + euler) and camera-clear parsing; scripts/test_run.py for build_command and camera/--clear/cycle --camera arg parsing. Confirm they fail.
2. Add Camera/CameraClear to HarnessCommandKind and TryParse.
3. Store the requested pose in the mod; re-apply from OnLateUpdate to PlayerCamera.Instance.camera.transform. No Harmony patch.
4. run.py: camera X Y Z --rot RX RY RZ, camera --clear, cycle --camera flag.
5. Verify in the running game on an edited Forest level: pose survives the game's own update through the settle period; check CameraOutlines/shaker do not move it back.
6. Document command, coordinate convention and caveats in docs/development.md; run task check; conventional commit without attribution.
Decision: harness-local, independent of TASK-005.01 (YAGNI). Runs after 004.08.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified under CrossOver on the sample test level (megabonklevels-test-level.mblevel.json), not a separately edited level: overhead pose held >6s of live gameplay and while frozen. The game never rewrites the camera transform, so camera-clear restores the saved local pose. Fog washes out the map above ~150 units.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added camera and camera-clear harness commands applied from OnLateUpdate (CameraOverride), run.py camera / camera --clear, and cycle --camera. Parsing is unit tested (tests written first). Documented with coordinate convention and fog caveat in docs/development.md. Kept harness-local; sharing with TASK-005.01 is left to that task.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
