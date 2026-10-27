---
id: TASK-011
title: Typing in the editor save-name box does nothing
status: In Progress
assignee: []
created_date: '2026-10-22T06:03:00Z'
updated_date: '2026-10-27 04:16'
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
In editor mode, real-keyboard typing did not work in the editor's text fields: characters and Backspace were rejected in the level-name (save) box and in the palette search box, so a level could not be saved under a chosen name or searched for by typing from a real keyboard. Harness-injected text worked in the same boxes, so the box focus and the text-handling code in EditorTileTools.HandleSaveTyping and TextFieldModel.Type were fine. Cause (confirmed with the RealInput diagnostic): under plain Wine (Wine Devel 11) on macOS the game receives key state through Input.GetKey and Input.GetKeyDown but Input.inputString is always empty, and TextFieldModel.Type reads characters, Backspace and Return only from that string. Return also never arrives as a key-down there (Wine shows its window title bar). It predates the TASK-007.04 pack changes and the input seam (seen on main at 833a39f). Clicking the game window did not help. An earlier retest that found typing working on the same setup is unexplained. Typing in the boxes is needed for manual editor checks.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A dev-only diagnostic logs, from the real-input layer of EditorInput (not the injected queue), each non-empty Input.inputString while an editor text field is focused (escaped, with char codes) and each real Backspace or Return key-down, so a real keypress shows in Latest.log whether or not the field accepts it
- [x] #2 With the diagnostic on, real keystrokes typed into the save-name box and the palette search box are tried in the running game and the log shows whether the game receives any characters from Wine, recorded as evidence in the task notes
- [x] #3 The cause is identified and recorded in docs/development.md, replacing the 'Real keyboard text' claim that typing works under plain Wine, including any runtime on which typing behaves differently
- [x] #4 Clicking the save-name box and typing on a real keyboard enters the typed characters, confirmed in the running game
- [x] #5 Clicking the palette search box and typing on a real keyboard enters the typed characters, confirmed in the running game
- [ ] #6 Backspace removes the last character and Enter saves the level under the typed name, confirmed in the running game
- [x] #7 Any testable logic changed has a failing test written first
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Diagnostic once the harness type command exists (TASK-010.03): inject the same text into the save-name box with it. If the box fills, the text-handling code in EditorTileTools.HandleSaveTyping is fine and the cause is that real keyboard text (Input.inputString) is not delivered under Wine; if it stays empty, the fault is in the box focus or the typing code. Injected text goes through EditorInput.InputString, so it does not exercise the real key path, which is the part under test.

Retest on macOS plain Wine after a fresh relaunch: click on the level-name box, real-keyboard typing, Backspace and Enter all worked; throwaway level deleted. The original failure did not reproduce and its cause is unconfirmed. No code changed, so no new test (AC #4 not applicable).

2026-10-26 reopened. During the TASK-007.04 in-game check on macOS plain Wine (Wine Devel 11, CrossOver Steam bottle used as the Wine prefix), real-keyboard typing and Backspace were rejected in both the save-name box and the palette search box. Clicking the game window to focus it did not change this. Harness type_text filled the save-name box and clicking Save wrote the level, so HandleSaveTyping, TextFieldModel.Type and the click-to-focus path work; the real Input.inputString half of EditorInput.InputString is the suspect.

Harness caveats found while testing: type_text only treats real control characters as Backspace (\b) and Return (\n); a literal backslash-n typed through the tool lands in the box as printable text. The key tool's Backspace and Return do not reach the text boxes, because TextFieldModel.Type reads text input rather than key state (only the caret keys use GetKeyDown). To clear a box through the harness, relaunch, or click Save instead of sending Return.

Next step is the diagnostic in AC #1: log raw Input.inputString and real Backspace/Return key-down while a field is focused, then press keys on a real keyboard. Empty inputString on keypress means Wine or the window is not delivering text to Unity; non-empty inputString with an unchanged box means the field is not consuming it.

Diagnostic landed (RealInputDiagnostic, EditorInput.LogRealTextInput, called from OnUpdate while DevHarness.Enabled and EditorMode.Active). It logs real keyboard frames whether or not a field has focus and records focused=true|false, which is slightly broader than AC #1 so a focus failure is distinguishable from a delivery failure. Usage is in docs/development.md under 'Real keyboard text'. Real-keyboard evidence for AC #2 is still to be collected.

Evidence 2026-10-26 (macOS, Wine Devel 11, game window clicked first, diagnostic from 795011f): real W/A/S/D moved the editor camera and a tool hotkey worked, so Input.GetKey and Input.GetKeyDown receive real keys, but no RealInput line appeared for any of those letter keys, so Input.inputString stayed empty. A real Backspace logged 'RealInput: Backspace down, focused=false' with no field focused and 'Backspace down, focused=true' with the save-name box focused after typing abc, and abc produced no inputString line. A real Return logged nothing and made Wine show its window title bar, so Return is intercepted at the Wine or Unity window level and never reaches Input.GetKeyDown. An earlier attempt right after a relaunch logged nothing for any key and is discounted because the game window probably lacked OS focus.

Conclusion so far: under this Wine setup the game receives key state but no text (Input.inputString is always empty), and Return does not arrive as a key-down. TextFieldModel.Type consumes characters, Backspace ('\b') and Return only from the text string, so none of the three can reach a text field. The earlier 'worked' retest is unexplained and may have used a different session state. Candidate fix: when inputString is empty, derive text from key-down state (letters, digits, punctuation, Shift) and take Backspace from GetKeyDown, with a US-layout assumption; Return needs a separate answer because Wine takes it.

Fix 9bcc0cf: EditorInput.InputString falls back to KeyTextMapper (US layout, Unity-free, 61 tests written first) over this frame's key-downs when Input.inputString is empty. Confirmed in the running game on macOS Wine Devel 11 with the real keyboard: typing with Shift and Backspace works in the save-name box and typing filters the palette search box. The log still shows only the Backspace key-down as RealInput, confirming the text came from the fallback. docs/development.md 'Real keyboard text' now records the cause and the fallback.

Open for AC #6: Backspace is confirmed. Enter-to-save is not: Return never arrives as a key-down under this Wine (it shows the Wine title bar) and the test keyboard has no numpad to try keypad Enter. Saving works through the Save button. Decide whether AC #6 should be narrowed to Backspace plus the Save button on Wine, or whether Return needs a Wine-side fix. Key repeat while holding a key is not implemented, because only key-downs are read.

Correction: the KeyTextMapper change added 51 tests (856 to 907), not 61.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
