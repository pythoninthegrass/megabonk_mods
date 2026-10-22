---
id: TASK-010.03
title: 'Harness key, mouse and type commands'
status: To Do
assignee: []
created_date: '2026-10-22 03:42'
labels:
  - dev-harness
  - tooling
dependencies:
  - TASK-010.01
  - TASK-010.02
references:
  - scripts/run.py
  - tests/test_run.py
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/harness_command.cs
  - src/MegabonkLevels.Mod/editor_input.cs
  - src/MegabonkLevels.Mod/injected_input.cs
  - tests/MegabonkLevels.Tests/harness_command_tests.cs
documentation:
  - docs/development.md
  - AGENTS.md
parent_task_id: TASK-010
priority: medium
ordinal: 56000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. Depends on TASK-010.01 (provides harness/results/<name> result files, the `Execute` return value and `read_result` in run.py) and TASK-010.02 (provides `InjectedInputQueue` and `EditorInput.Queue` with `EnqueueTap`, `EnqueueKeyDown`, `EnqueueKeyUp`, `EnqueueMouseMove`, `EnqueueClick`, `EnqueueMouseDown`, `EnqueueMouseUp`, `EnqueueText`, `ClearMouse`). Do not start until both are merged. Can run in parallel with TASK-010.05 and TASK-010.06.

Goal: let a shell script or agent press keys, move and click the mouse, and type text in the running game by feeding the injected-input queue, so editor features (palette search, tool hotkeys, object rotation, clicking objects) can be exercised without OS input or window focus.

Wire formats (decided):
- `{"command":"key","action":"tap","key":"R","modifiers":["LeftShift"]}`; `action` is `tap`, `down` or `up`; `modifiers` is optional and only valid for `tap`. `key` is a `UnityEngine.KeyCode` member name, matched case-sensitively.
- `{"command":"mouse","action":"move","x":960,"y":540}`; `action` is `move`, `click`, `down`, `up` or `clear`. `x` and `y` are required for `move`; `click`, `down` and `up` take an optional `button` (0 left, 1 right, 2 middle; default 0) and an optional `x`/`y` that moves first. `clear` drops the injected mouse position so the real mouse is used again.
- `{"command":"type","text":"chest"}`; max 200 characters; `\b` is backspace and `\n` is return.
- Coordinates are screenshot pixels with the origin at the top left (what an agent sees in a harness screenshot). The mod converts to Unity's bottom-left origin using `Screen.height`; keep the conversion as a pure function `ScreenPoint.ToUnity(float x, float y, int screenHeight)` in a Unity-free file linked into the tests.
- An unknown key name, an unknown action, a missing required field or an out-of-range button is rejected at parse time with a clear error, which TASK-010.01's result file reports as `ok:false`. Validation of key names must not need Unity: keep a Unity-free list of valid names (copy the member names of `UnityEngine.KeyCode` for the keys the editor uses plus all letters, digits as `Alpha0`-`Alpha9`, `Keypad0`-`Keypad9`, F1-F12, arrows, Escape, Return, Backspace, Delete, Space, Tab, LeftShift, RightShift, LeftControl, RightControl, LeftAlt, RightAlt) in `src/MegabonkLevels.Mod/key_names.cs`, and add a Unity-side test-less sanity check at startup that logs any listed name `Enum.TryParse<KeyCode>` rejects.

Steps (TDD): 1) failing xUnit tests in harness_command_tests.cs for `TryParse` of each new command (valid forms, every rejection case above) and for `ScreenPoint.ToUnity`; 2) failing Python tests in tests/test_run.py for the new subcommands building the exact payloads; 3) add `Key`, `Mouse` and `Type` to `HarnessCommandKind` and `TryParse`; carry the extra fields on `HarnessCommand` without breaking existing positional constructions (add new optional members, or a nested `InputArgs` record); 4) `Execute` forwards to `EditorInput.Queue`; the result for each is null; 5) run.py: `key <name> [--mod LeftShift ...]`, `key --down <name>`, `key --up <name>`, `mouse move X Y`, `mouse click [--button N] [X Y]`, `mouse down|up`, `mouse clear`, `type <text>`; update the docstring usage; 6) `task check`; 7) in the game: relaunch; send `mouse move` + `mouse click` on a palette entry and `type "chest"` into the palette, then `key tap R` with an object selected; take a screenshot after each and read it to confirm the effect; 8) document the commands, wire formats, coordinate convention and the valid key names in docs/development.md.

Do not: simulate input through the OS, touch Rewired, or accept key names that are not in the valid list.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 key, mouse and type commands parse and validate as specified, with unknown keys, unknown actions, missing fields and bad buttons rejected with a clear error
- [ ] #2 Mouse coordinates are interpreted as screenshot pixels with a top-left origin and converted to Unity's bottom-left origin by a tested pure function
- [ ] #3 Execute feeds the commands into EditorInput.Queue, and the injected input reaches the editor with the game window unfocused
- [ ] #4 run.py has key, mouse and type subcommands that build the documented payloads
- [ ] #5 Confirmed in the running game with screenshots: a click selects a palette entry, typed text appears in the palette search or the focused text field, and a key tap triggers an editor hotkey
- [ ] #6 Parsing, validation, coordinate conversion and run.py payloads have tests written first
- [ ] #7 docs/development.md documents the commands, wire formats, coordinate convention and valid key names
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
