---
id: TASK-011
title: Typing in the editor save-name box does nothing
status: Done
assignee: []
created_date: '2026-10-22T06:03:00Z'
updated_date: '2026-10-23T02:06:00Z'
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
ordinal: 61000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In editor mode, clicking the save-name box and typing produces no characters, so a level cannot be saved under a chosen name from the editor. Found while manually verifying the editor input seam (TASK-010.02): it fails identically on the build without that change (main at 833a39f) and on the build with it, so it predates the seam and is not caused by it. Other editor input (palette clicks, fly camera, tool hotkeys, rotation) was not reported broken. Observed on macOS under plain Wine (Wine Devel 11) with the game started through scripts/run.py relaunch. It is not yet known whether the cause is the game window not receiving text input under Wine, the click not focusing the box, or the text-handling code in EditorTileTools.HandleSaveTyping; the cause is unconfirmed and the same check on another runtime (CrossOver, Windows) would narrow it. Typing in the box is needed for manual editor checks; it does not block the MCP harness work in TASK-010, but should be fixed before returning to the other outstanding editor and harness tasks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Clicking the save-name box in editor mode and typing on a real keyboard enters the typed characters, confirmed in the running game
- [x] #2 Backspace removes the last character and Enter saves the level under the typed name, confirmed in the running game
- [x] #3 The cause is recorded in docs/development.md, including any runtime on which typing behaves differently
- [x] #4 Any testable logic changed has a failing test written first
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Diagnostic once the harness type command exists (TASK-010.03): inject the same text into the save-name box with it. If the box fills, the text-handling code in EditorTileTools.HandleSaveTyping is fine and the cause is that real keyboard text (Input.inputString) is not delivered under Wine; if it stays empty, the fault is in the box focus or the typing code. Injected text goes through EditorInput.InputString, so it does not exercise the real key path, which is the part under test.

Retest on macOS plain Wine after a fresh relaunch: click on the level-name box, real-keyboard typing, Backspace and Enter all worked; throwaway level deleted. The original failure did not reproduce and its cause is unconfirmed. No code changed, so no new test (AC #4 not applicable).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Closed as unreproduced. Real-keyboard text entry, Backspace and Enter work in the save-name box under plain Wine on macOS. No code change. docs/development.md gains a 'Real keyboard text' section recording the result and the open questions (window focus, intermittency; CrossOver and Windows not compared).
<!-- SECTION:FINAL_SUMMARY:END -->
