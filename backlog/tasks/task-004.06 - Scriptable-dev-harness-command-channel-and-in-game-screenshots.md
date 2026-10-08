---
id: TASK-004.06
title: 'Scriptable dev harness: command channel and in-game screenshots'
status: To Do
assignee: []
created_date: '2026-10-08 02:13'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-004
priority: medium
ordinal: 37000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Right now, exercising the mod in the running game means pressing F6 and driving menus with OS-level key presses (osascript on macOS, a KVM on the Linux host). That was unreliable in TASK-004.02: the idle player died within about 20 seconds, the level-up dialog blocked input, there was no mouse input, and screenshots came from the host screen rather than the game. Add a small development-only harness inside the MelonLoader mod so a shell script can run a load-and-check cycle without simulating input: trigger a level load, capture the game's own frame, and quit. Read docs/level-format.md (runtime playback section) and docs/modding-setup.md first; the mod already loads a level and applies its edits when F6 is pressed.

Open design choices to settle during planning, not here: file-drop watcher versus localhost listener, and how the harness is enabled (env var versus config file). Under Wine/CrossOver, localhost networking and ScreenCapture.CaptureScreenshot are untested; confirm both before committing to them.

Out of scope, deliberately deferred to a future task because each needs reverse-engineering of game internals that has not been done: making the player invulnerable, skipping the level-up dialog, moving the player/camera, and invoking menu buttons programmatically.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A script outside the game can trigger loading a given level file without a keypress and without the file having a hardcoded name, and the run starts with its edits applied
- [ ] #2 A script can request a screenshot of the game's own rendered frame to a chosen path, and the file is a valid image of the running scene
- [ ] #3 A script can request that the game quit cleanly, and the log records that it did
- [ ] #4 An unrecognised or malformed command logs a clear warning and does not crash or change game state
- [ ] #5 The harness is off by default, so a normal player install exposes no command channel unless it is explicitly enabled
- [ ] #6 Verified end to end on the macOS/CrossOver install: launch, load a level, take a screenshot, quit, all from the shell with no osascript key presses after launch
- [ ] #7 Pure command parsing is unit tested, with the tests written before the implementation
- [ ] #8 The commands, how to enable the harness, and any Wine/CrossOver caveats are documented
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
