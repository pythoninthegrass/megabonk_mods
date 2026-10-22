---
id: TASK-010.02
title: Injected-input seam for editor input
status: To Do
assignee: []
created_date: '2026-10-22 03:42'
labels:
  - dev-harness
  - tooling
dependencies: []
references:
  - src/MegabonkLevels.Mod/editor_mode.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
  - src/MegabonkLevels.Mod/editor_object_tools.cs
  - src/MegabonkLevels.Mod/editor_palette.cs
  - src/MegabonkLevels.Mod/megabonk_levels_mod.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
documentation:
  - docs/development.md
  - AGENTS.md
parent_task_id: TASK-010
priority: medium
ordinal: 55000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. No dependencies; can run in parallel with TASK-010.01 and TASK-010.04. This task adds the seam only; the harness commands that feed it are TASK-010.03.

Problem: the editor reads input through 34 raw `UnityEngine.Input` calls in 5 files (editor_mode.cs 8, editor_tile_tools.cs 14, editor_object_tools.cs 8, editor_palette.cs 2, megabonk_levels_mod.cs 2; find them with `rg 'Input\.(GetKey|GetMouse|mousePosition|inputString|GetAxis)' src`). Nothing outside the real keyboard and mouse can drive them. Route them all through one static so input can be injected.

Design (decided, do not change; TASK-010.03 builds on it):
1. New Unity-free file `src/MegabonkLevels.Mod/injected_input.cs` with `InjectedInputQueue`, linked into the test project (add a `<Compile Include=... Link=...>` entry like the existing ones). Keys are identified by `UnityEngine.KeyCode` enum member names as strings (`"R"`, `"LeftShift"`, `"Alpha1"`, `"Escape"`), so the queue never references Unity.
2. Queue API (names are fixed): `EnqueueTap(string key, IReadOnlyList<string> modifiers)`, `EnqueueKeyDown(string key)`, `EnqueueKeyUp(string key)`, `EnqueueMouseMove(float x, float y)` (screen pixels, origin bottom-left, already converted), `EnqueueClick(int button)`, `EnqueueMouseDown(int button)`, `EnqueueMouseUp(int button)`, `EnqueueText(string text)`, `ClearMouse()`, `BeginFrame(int frame)`, and the query side `IsKeyHeld(string)`, `WasKeyPressedThisFrame(string)`, `WasKeyReleasedThisFrame(string)`, `IsMouseHeld(int)`, `WasMousePressedThisFrame(int)`, `WasMouseReleasedThisFrame(int)`, `MousePosition` (`(float, float)?`, null until a move is queued or after `ClearMouse`), `InputStringThisFrame`.
3. Frame semantics: each enqueue schedules steps on consecutive frames starting at the next `BeginFrame`. Tap with N as its first frame: modifiers down at N, key down at N+1, key up at N+2, modifiers up at N+3. Click: move already applied, button down at N, button up at N+1. Text: one character per frame into `InputStringThisFrame` (`\b` is backspace, `\n` is return). Pressed/released flags are true for exactly one frame. A held key stays held until its key-up step. An injected mouse position persists until `ClearMouse`. Calling `BeginFrame` twice with the same frame number is a no-op.
4. New Unity-side static `src/MegabonkLevels.Mod/editor_input.cs` (not linked into tests): `EditorInput` exposes `GetKey(KeyCode)`, `GetKeyDown(KeyCode)`, `GetKeyUp(KeyCode)`, `GetMouseButton(int)`, `GetMouseButtonDown(int)`, `GetMouseButtonUp(int)`, `MousePosition` (`Vector2`) and `InputString`. Each returns the real `UnityEngine.Input` value OR the injected one (for position: injected if set, else real; for text: real string plus injected). Hold the single shared `InjectedInputQueue` instance as `EditorInput.Queue`.
5. Call `EditorInput.Queue.BeginFrame(Time.frameCount)` at the very top of `OnUpdate` in megabonk_levels_mod.cs, before `DevHarness.Poll()` and before any editor code runs.
6. Replace every raw `Input.*` read in the 5 files with the matching `EditorInput` member. Behaviour with no injected input must be identical to today.

Steps (TDD): 1) failing xUnit tests for `InjectedInputQueue` in `tests/MegabonkLevels.Tests/injected_input_tests.cs`: tap timing with and without modifiers, pressed/released last one frame, held persists, click timing, text one char per frame including backspace and return, mouse position persists and `ClearMouse` resets, repeated `BeginFrame` is a no-op, an unknown key name still queues (validation belongs to TASK-010.03); 2) implement the queue; 3) implement `EditorInput` and swap the call sites; 4) `task check`; 5) in the game: `task mod:build`, `uv run scripts/run.py relaunch`, confirm with a screenshot that the editor still responds to the real keyboard and mouse (Lance can test the real input; an agent cannot) and that the log shows no new errors; 6) document the seam in docs/development.md (what it is, the frame semantics, where `EditorInput` is called).

Done check: `rg 'Input\.(GetKey|GetMouse|mousePosition|inputString|GetAxis)' src` returns matches only inside editor_input.cs.

Do not: add harness commands (TASK-010.03), touch the game's Rewired input, or change editor behaviour.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 InjectedInputQueue exists as a Unity-free class with the documented API and frame semantics, linked into the test project
- [ ] #2 EditorInput returns the real UnityEngine.Input value or the injected one for key, mouse button, mouse position and input string reads
- [ ] #3 EditorInput.Queue.BeginFrame(Time.frameCount) runs at the top of OnUpdate before the harness poll and any editor code
- [ ] #4 A raw-Input search over src finds matches only in editor_input.cs, and with no injected input the editor behaves as before, checked in the running game
- [ ] #5 Queue behaviour (tap timing, pressed/released one frame, hold, click, text with backspace and return, mouse persistence and clear, repeated BeginFrame) has xUnit tests written first
- [ ] #6 docs/development.md describes the seam and its frame semantics
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
