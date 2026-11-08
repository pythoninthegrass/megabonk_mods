---
id: TASK-054.03
title: >-
  Tilde-toggled console overlay that slides up from the bottom and pauses the
  run
status: To Do
assignee: []
created_date: '2026-11-08T07:54:00Z'
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
- **Look:** a dark grey, translucent panel anchored to the bottom edge, roughly 40% of screen height. It has a scrollback area and a single input line with a caret, and uses the mod's existing look (the game's RobotoMono TMP font and the shared editor UI helpers and palette). The open/close slide is short and uses unscaled time, so it still animates while the game is paused.
- **Toggle key:** backquote/tilde opens and closes it, and the toggling character must not land in the input line. It must not open while the game's own F10 `DebugConsole` is active. The mod's F6–F9 hotkeys and the editor's hotkeys must not fire while the console has focus.
- **Keys while open:** Enter runs the line and echoes it plus the reply into scrollback. Up/Down walk history, Tab completes, PageUp/PageDown scroll, Left/Right/Home/End/Delete/Backspace edit, and Esc closes the console. Esc must not also open the game's pause menu.
- **Pause:** opening pauses the run and closing restores whatever pause state existed before. A console opened inside the already-frozen editor must leave the editor frozen on close. The cursor is visible and unlocked while open, and its previous state is restored on close.
- **Input path:** read input only through the mod's virtual input layer (`EditorInput`), never `UnityEngine.Input` directly. The layer handles the Wine empty-`inputString` workaround and harness key/text injection. Add the console's keys (BackQuote, PageUp, PageDown, Home, End) to the harness key-name allow-list, so the harness `key` command can drive the console.
- **Visibility to tooling:** register the console's widgets so harness `ui-tree`/`click-widget` can see them.
- **Frame cost:** drive the console from the mod's per-frame update, following the existing tick and perf-timer pattern. Do not add an injected MonoBehaviour. Il2Cpp interop rules in docs/development.md apply.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Backquote/tilde opens and closes the console in a run, in editor mode, and on the main menu; the toggle character is never typed into the input line
- [ ] #2 The panel is dark grey and translucent, anchored to the bottom edge, and slides in and out while the game is paused (screenshot attached to the task as evidence)
- [ ] #3 Opening pauses the run; closing restores the prior pause state, and an editor session stays frozen after the console closes
- [ ] #4 The cursor is visible and unlocked while open and restored on close
- [ ] #5 Enter, Up/Down, Tab, PageUp/PageDown, the caret-editing keys and Esc behave as described; Esc does not open the pause menu
- [ ] #6 The console does not open while the game's F10 DebugConsole is active, and F6-F9 and editor hotkeys do not fire while the console is focused
- [x] #7 The harness key command accepts BackQuote, PageUp, PageDown, Home and End, with tests for the allow-list
- [ ] #8 Console widgets appear in harness ui-tree output
- [x] #9 docs/development.md documents keys, pause behaviour and the DebugConsole interaction
<!-- AC:END -->

## Needs live verification

Everything below is implemented and builds clean, but I cannot launch or see the game from this checkout, so it has no in-game evidence yet and stays unchecked. None of it was fabricated:

- **#1** Toggle opens/closes in a run, in the editor, and on the main menu; the backquote character never lands in the input line (the toggle character is dropped from the frame's text in `ConsoleOverlay.ReadInput`, but this needs an in-game key press to confirm).
- **#2** Dark translucent bottom panel slides in/out while paused — needs a screenshot; none captured.
- **#3** Pause-on-open / restore-on-close, and the frozen-editor case, are unit tested in `console_state_tests.cs` (`ShouldPauseOnOpen`, `ShouldUnpauseOnClose`), but the `MyTime` call sites and the editor-stays-frozen behaviour across a real load need the live game.
- **#4** Cursor visible/unlocked while open and restored on close — set in `OpenConsole`/`CloseConsole`, needs the live game.
- **#5** Enter/Up/Down/Tab/PageUp/PageDown/caret keys/Esc behave as described and Esc does not open the pause menu — the `PauseUi.Toggle` prefix suppression needs the live game.
- **#6** No open while the game's F10 DebugConsole is active (`ConsoleState.Toggle` returns Stay, unit tested for the branch) and F6-F9/editor hotkeys suppressed while focused — the mod hotkey skip and the DebugConsole `IsActive` check need the live game.
- **#8** `ConsoleInput`/`ConsoleScrollback`/`ConsolePanel` registered for harness `ui-tree`/`click-widget` — wired in `DevHarness.EditorWidgets`, needs the live game to see them in output.

Verified with a test or build I ran: #7 (allow-list, `KeyNames_ListsTheDocumentedGroupsAndNoDuplicates` + the MCP mirror test), #9 (docs), and the pure-logic layer behind #3/#6 via `console_state_tests.cs`.

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
