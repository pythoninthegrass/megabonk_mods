---
id: TASK-004.09
title: 'Dev harness: camera pose command'
status: To Do
assignee: []
created_date: '2026-10-08 03:41'
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
- [ ] #1 A harness command sets the camera position and euler rotation, and a matching command clears the override and returns control to the game, with each logged
- [ ] #2 A screenshot taken after the command shows the requested view, not the game's own pose, verified on an edited Forest level
- [ ] #3 The pose survives the game's own camera update for the whole settle period
- [ ] #4 `run.py camera` and `run.py camera --clear` subcommands exist, and `cycle` accepts a camera pose flag
- [ ] #5 Pure command parsing for the new command is unit tested, with the tests written before the implementation
- [ ] #6 The command, its coordinate convention, and any caveats are documented in docs/development.md
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
