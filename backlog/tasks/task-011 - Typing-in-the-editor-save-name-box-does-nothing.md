---
id: TASK-011
title: Typing in the editor save-name box does nothing
status: To Do
assignee: []
created_date: '2026-10-22T06:03:00Z'
labels:
  - editor
  - bug
dependencies: []
references:
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
  - src/MegabonkLevels.Mod/editor_input.cs
documentation:
  - docs/development.md
priority: high
type: bug
ordinal: 61000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In editor mode, clicking the save-name box and typing produces no characters, so a level cannot be saved under a chosen name from the editor. Found while manually verifying the editor input seam (TASK-010.02): it fails identically on the build without that change (main at 833a39f) and on the build with it, so it predates the seam and is not caused by it. Other editor input (palette clicks, fly camera, tool hotkeys, rotation) was not reported broken. Observed on macOS under plain Wine (Wine Devel 11) with the game started through scripts/run.py relaunch. It is not yet known whether the cause is the game window not receiving text input under Wine, the click not focusing the box, or the text-handling code in EditorTileTools.HandleSaveTyping; the cause is unconfirmed and the same check on another runtime (CrossOver, Windows) would narrow it. Typing in the box is needed for manual editor checks; it does not block the MCP harness work in TASK-010, but should be fixed before returning to the other outstanding editor and harness tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Clicking the save-name box in editor mode and typing on a real keyboard enters the typed characters, confirmed in the running game
- [ ] #2 Backspace removes the last character and Enter saves the level under the typed name, confirmed in the running game
- [ ] #3 The cause is recorded in docs/development.md, including any runtime on which typing behaves differently
- [ ] #4 Any testable logic changed has a failing test written first
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
