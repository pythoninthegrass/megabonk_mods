---
id: TASK-011
title: Typing in the editor save-name box does nothing
status: To Do
assignee: []
created_date: '2026-10-22T06:03:00Z'
updated_date: '2026-10-27 03:55'
labels:
  - editor
  - bug
dependencies: []
references:
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
  - src/MegabonkLevels.Mod/editor_input.cs
  - src/MegabonkLevels.Mod/text_field_model.cs
  - docs/development.md
documentation:
  - docs/development.md
priority: high
ordinal: 61000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In editor mode, real-keyboard typing does not work in the editor's text fields: characters and Backspace are rejected in the level-name (save) box and in the palette search box, so a level cannot be saved under a chosen name or searched for by typing from a real keyboard. Harness-injected text works in the same boxes, so the box focus and the text-handling code in EditorTileTools.HandleSaveTyping and TextFieldModel.Type are fine; the failure is on the real-input half of EditorInput (Input.inputString and key state), which the injected path bypasses. Observed on macOS under plain Wine (Wine Devel 11) with the game started through scripts/run.py relaunch, on a build with the TASK-007.04 pack changes (which do not touch input) and earlier on main at 833a39f (before the input seam), so it predates both. Clicking the game window first, to give it OS focus, does not help. An earlier retest found real-keyboard typing working on the same setup and closed this as unreproduced, so the failure is intermittent or depends on session state; the cause is unconfirmed. Typing in the boxes is needed for manual editor checks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A dev-only diagnostic logs, from the real-input layer of EditorInput (not the injected queue), each non-empty Input.inputString while an editor text field is focused (escaped, with char codes) and each real Backspace or Return key-down, so a real keypress shows in Latest.log whether or not the field accepts it
- [ ] #2 With the diagnostic on, real keystrokes typed into the save-name box and the palette search box are tried in the running game and the log shows whether the game receives any characters from Wine, recorded as evidence in the task notes
- [ ] #3 The cause is identified and recorded in docs/development.md, replacing the 'Real keyboard text' claim that typing works under plain Wine, including any runtime on which typing behaves differently
- [ ] #4 Clicking the save-name box and typing on a real keyboard enters the typed characters, confirmed in the running game
- [ ] #5 Clicking the palette search box and typing on a real keyboard enters the typed characters, confirmed in the running game
- [ ] #6 Backspace removes the last character and Enter saves the level under the typed name, confirmed in the running game
- [ ] #7 Any testable logic changed has a failing test written first
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Diagnostic once the harness type command exists (TASK-010.03): inject the same text into the save-name box with it. If the box fills, the text-handling code in EditorTileTools.HandleSaveTyping is fine and the cause is that real keyboard text (Input.inputString) is not delivered under Wine; if it stays empty, the fault is in the box focus or the typing code. Injected text goes through EditorInput.InputString, so it does not exercise the real key path, which is the part under test.

Retest on macOS plain Wine after a fresh relaunch: click on the level-name box, real-keyboard typing, Backspace and Enter all worked; throwaway level deleted. The original failure did not reproduce and its cause is unconfirmed. No code changed, so no new test (AC #4 not applicable).

2026-10-26 reopened. During the TASK-007.04 in-game check on macOS plain Wine (Wine Devel 11, CrossOver Steam bottle used as the Wine prefix), real-keyboard typing and Backspace were rejected in both the save-name box and the palette search box. Clicking the game window to focus it did not change this. Harness type_text filled the save-name box and clicking Save wrote the level, so HandleSaveTyping, TextFieldModel.Type and the click-to-focus path work; the real Input.inputString half of EditorInput.InputString is the suspect.

Harness caveats found while testing: type_text only treats real control characters as Backspace (\b) and Return (\n); a literal backslash-n typed through the tool lands in the box as printable text. The key tool's Backspace and Return do not reach the text boxes, because TextFieldModel.Type reads text input rather than key state (only the caret keys use GetKeyDown). To clear a box through the harness, relaunch, or click Save instead of sending Return.

Next step is the diagnostic in AC #1: log raw Input.inputString and real Backspace/Return key-down while a field is focused, then press keys on a real keyboard. Empty inputString on keypress means Wine or the window is not delivering text to Unity; non-empty inputString with an unchanged box means the field is not consuming it.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
