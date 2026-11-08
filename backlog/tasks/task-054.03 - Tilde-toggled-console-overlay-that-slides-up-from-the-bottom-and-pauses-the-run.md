---
id: TASK-054.03
title: >-
  Tilde-toggled console overlay that slides up from the bottom and pauses the
  run
status: Done
assignee: []
created_date: '2026-11-08T07:54:00Z'
updated_date: '2026-11-08T18:18:00Z'
labels: []
dependencies:
  - TASK-054.01
  - TASK-054.02
references:
  - src/MegabonkLevels.Mod/editor_ui.cs
  - src/MegabonkLevels.Mod/editor_settings_panel.cs
  - src/MegabonkLevels.Mod/text_field_view.cs
  - src/MegabonkLevels.Mod/editor_input.cs
  - src/MegabonkLevels.Mod/key_text_mapper.cs
  - src/MegabonkLevels.Mod/key_names.cs
  - src/MegabonkLevels.Mod/editor_pause_input_patch.cs
  - src/MegabonkLevels.Mod/editor_text_input_policy.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
  - src/MegabonkLevels.Mod/editor_mode.cs
  - src/MegabonkLevels.Mod/megabonk_levels_mod.cs
documentation:
  - docs/development.md
parent_task_id: TASK-054
priority: medium
type: feature
ordinal: 194000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
This is the visible part of the in-game console (TASK-054). It is a Fallout 4-style drop-down, except that it slides up from the bottom of the screen. The command language, history, completion and scrollback come from TASK-054.02. Command execution goes through the in-process harness entry point from TASK-054.01.

Requirements and constraints the maintainer fixed or that the codebase imposes:
- **Look:** a dark grey, translucent panel anchored to the bottom edge, roughly 40% of screen height, laid out like a terminal: one column of text rows with the `>` prompt and caret inline as the last row of the output, and long lines wrapped. It uses the mod's existing look (the game's RobotoMono TMP font and the shared editor UI helpers and palette). The open/close slide is short and uses unscaled time, so it still animates while the game is paused.
- **Toggle key:** backquote/tilde opens and closes it, and the toggling character must not land in the input line. It must not open while the game's own F10 `DebugConsole` is active. The mod's F6–F9 hotkeys and the editor's hotkeys must not fire while the console has focus.
- **Keys while open:** Enter runs the line and echoes it plus the reply into scrollback. Up/Down walk history, Tab completes, PageUp/PageDown scroll, Left/Right/Home/End/Delete/Backspace edit, and Esc closes the console. Esc must not also open the game's pause menu.
- **Pause:** opening pauses the run and closing restores whatever pause state existed before. A console opened inside the already-frozen editor must leave the editor frozen on close. The cursor is visible and unlocked while open, and its previous state is restored on close.
- **Input path:** read input only through the mod's virtual input layer (`EditorInput`), never `UnityEngine.Input` directly. The layer handles the Wine empty-`inputString` workaround and harness key/text injection. Add the console's keys (BackQuote, PageUp, PageDown, Home, End) to the harness key-name allow-list, so the harness `key` command can drive the console.
- **Visibility to tooling:** register the console's widgets so harness `ui-tree`/`click-widget` can see them.
- **Frame cost:** drive the console from the mod's per-frame update, following the existing tick and perf-timer pattern. Do not add an injected MonoBehaviour. Il2Cpp interop rules in docs/development.md apply.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Backquote/tilde opens and closes the console in a run, in editor mode, and on the main menu; the toggle character is never typed into the input line
- [x] #2 The panel is dark grey and translucent, anchored to the bottom edge, and slides in and out while the game is paused (screenshot attached to the task as evidence)
- [x] #3 Opening pauses the run; closing restores the prior pause state, and an editor session stays frozen after the console closes
- [x] #4 The cursor is visible and unlocked while open and restored on close
- [x] #5 Enter, Up/Down, Tab, PageUp/PageDown, the caret-editing keys and Esc behave as described; Esc does not open the pause menu
- [x] #6 The console does not open while the game's F10 DebugConsole is active, and F6-F9 and editor hotkeys do not fire while the console is focused
- [x] #7 The harness key command accepts BackQuote, PageUp, PageDown, Home and End, with tests for the allow-list
- [x] #8 Console widgets appear in harness ui-tree output
- [x] #9 docs/development.md documents keys, pause behaviour and the DebugConsole interaction
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
#4 verified live through the new `cursorVisible`/`cursorLocked` fields of the harness `state` result: in a run the cursor is hidden and locked, with the console open it is visible and unlocked, and after close it is hidden and locked again. Screenshot of the open panel (dark, translucent, bottom-anchored, paused run): .tools/evidence/task-054-03-console-open.png.
#2 and #6 verified by the maintainer in the running game: the panel slides in and out while paused, and the console does not open while the F10 DebugConsole is active.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added the tilde-toggled console overlay: a dark grey, translucent, terminal-style panel anchored to the bottom (about 40% of the screen) that slides on unscaled time, pauses the run and restores the prior pause and cursor state on close, and is driven through EditorInput from the mod's per-frame update. Harness key allow-list covers BackQuote, PageUp, PageDown, Home and End; console widgets show in ui_tree; F6-F9 and editor hotkeys are gated while it has focus, including the F7 coordinate toggle fixed during verification. This session added `cursorVisible` and `cursorLocked` to the harness `state` result (unit tested, documented) so the cursor behaviour could be checked live. Verification: unit tests and build pass; driven live through the harness for toggle, pause, keys, ui_tree and cursor; slide and F10 DebugConsole behaviour confirmed by the maintainer. Evidence screenshot: .tools/evidence/task-054-03-console-open.png (gitignored).
<!-- SECTION:FINAL_SUMMARY:END -->

## Live verification

Driven in the running game through the harness (`key`, `type_text`, `state`, `ui_tree`, `screenshot`, `log_tail`).

Verified:
- **#1** The toggle opens and closes the console on the main menu (no run), in a live run and in editor mode. The placeholder stayed visible after every open, so the backquote never landed in the input line.
- **#3** In a run the log shows `MyTime.paused=True` on open and `False` on close, `state` reports `frozen: true` while open and `false` after, and the timer resumes. Opened inside the editor, `frozen` and `editor` stay true after close and the log shows `paused=True` at close. On the main menu nothing is paused on open.
- **#5** Enter runs the line and echoes it; Tab completes `sta` to `state `; Home, Delete, End and Backspace edit as expected; Left and Right move the caret (`ab` became `aXbY`); Up recalls history and Down walks back to an empty line; PageUp scrolls the scrollback and PageDown returns; Esc closes the console without opening the game's pause menu, in the editor and in a run.
- **#8** `ui_tree` lists `ConsoleInput`, `ConsoleScrollback` and `ConsolePanel`.
- **#6, partly** F8 and F7 do nothing while the console is open.

Not met or not observed:
- **#6** F7 used to toggle the coordinate readout while the console had focus, because `position_label.cs` read it outside the `ConsoleOverlay.Focused` early return. It now passes the console's focus into `PositionReadout.ShouldToggle` (unit tested) and was re-checked live: F7 with the console open leaves `coordinatesEnabled` false, and F7 after closing it toggles again. F6 and F9 sit behind the early return and F8 is gated in `editor_mode.cs`. The F10 `DebugConsole` case cannot be driven live: an injected F10 never reaches the game's own input, so only the `ConsoleState.Toggle` unit tests cover it, and #6 stays unchecked for that reason.
- **#2** The panel is dark, translucent, anchored to the bottom and about 40% of the screen, and it renders while the run is paused. The slide itself lasts 0.12 s on unscaled time, too short to capture, so it is covered by the `Slide_*` unit tests only.
- **#4** The cursor visibility and lock state have no live probe. `ConsoleState.ShouldRestoreCursor` is unit tested, but nothing in the harness reads the cursor.

The panel's layout changed after this task was written: it is now one terminal-style column with the prompt inline as the last row and no separate input row (see "In-game console" in docs/development.md).
