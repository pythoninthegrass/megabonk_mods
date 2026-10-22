---
id: TASK-010.02
title: Injected-input seam for editor input
status: In Progress
assignee: []
created_date: '2026-10-22 03:42'
updated_date: '2026-10-22T05:51:00Z'
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

Problem: the editor reads input through 36 raw `UnityEngine.Input` calls in 5 files (editor_mode.cs 8, editor_tile_tools.cs 15, editor_object_tools.cs 8, editor_palette.cs 3, megabonk_levels_mod.cs 2; find them with `rg 'Input\.(GetKey|GetMouse|mousePosition|inputString|GetAxis|mouseScrollDelta)' src`). Nothing outside the real keyboard and mouse can drive them. Route them all through one static so input can be injected.

Design (decided, do not change; TASK-010.03 builds on it):
1. New Unity-free file `src/MegabonkLevels.Mod/injected_input.cs` with `InjectedInputQueue`, linked into the test project (add a `<Compile Include=... Link=...>` entry like the existing ones in tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj). Keys are identified by `UnityEngine.KeyCode` enum member names as strings (`"R"`, `"LeftShift"`, `"Alpha1"`, `"Escape"`), so the queue never references Unity.
2. Queue API (names are fixed): `EnqueueTap(string key, IReadOnlyList<string> modifiers)`, `EnqueueKeyDown(string key)`, `EnqueueKeyUp(string key)`, `EnqueueMouseMove(float x, float y)` (screen pixels, origin bottom-left, already converted), `EnqueueClick(int button)`, `EnqueueMouseDown(int button)`, `EnqueueMouseUp(int button)`, `EnqueueText(string text)`, `ClearMouse()`, `BeginFrame(int frame)`, and the query side `IsKeyHeld(string)`, `WasKeyPressedThisFrame(string)`, `WasKeyReleasedThisFrame(string)`, `IsMouseHeld(int)`, `WasMousePressedThisFrame(int)`, `WasMouseReleasedThisFrame(int)`, `MousePosition` (`(float, float)?`, null until a move is queued or after `ClearMouse`), `InputStringThisFrame`.
3. Frame semantics: each enqueue schedules steps on consecutive frames starting at the next `BeginFrame`. Tap with N as its first frame: modifiers down at N, key down at N+1, key up at N+2, modifiers up at N+3. Click: move already applied, button down at N, button up at N+1. Text: one character per frame into `InputStringThisFrame` (`\b` is backspace, `\n` is return). Pressed/released flags are true for exactly one frame. A held key stays held until its key-up step. An injected mouse position persists until `ClearMouse`. Calling `BeginFrame` twice with the same frame number is a no-op.
4. New Unity-side static `src/MegabonkLevels.Mod/editor_input.cs` (not linked into tests): `EditorInput` exposes `GetKey(KeyCode)`, `GetKeyDown(KeyCode)`, `GetKeyUp(KeyCode)`, `GetMouseButton(int)`, `GetMouseButtonDown(int)`, `GetMouseButtonUp(int)`, `MousePosition` (`Vector2`) and `InputString`. Each returns the real `UnityEngine.Input` value OR the injected one (for position: injected if set, else real; for text: real string plus injected). It also exposes two pass-throughs that return the real value only, because injecting axes and scrolling is out of scope: `GetAxisRaw(string)` (used by the free-fly look in editor_mode.cs) and `MouseScrollDelta` (`Vector2`, used by the palette and the level list). Hold the single shared `InjectedInputQueue` instance as `EditorInput.Queue`.
5. Call `EditorInput.Queue.BeginFrame(Time.frameCount)` at the very top of `OnUpdate` in megabonk_levels_mod.cs, before `DevHarness.Poll()` and before any editor code runs.
6. Replace every raw `Input.*` read in the 5 files with the matching `EditorInput` member. Behaviour with no injected input must be identical to today: same method (`GetKey` stays `GetKey`, `GetKeyDown` stays `GetKeyDown`), same arguments, same results.

Verification you can run unattended, and the commands to avoid:
- Run the Unity-free tests with `dotnet test tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj` (equivalently `task mod:test`).
- Compile the Unity-side code with `dotnet build src/MegabonkLevels.Mod/MegabonkLevels.Mod.csproj -p:ModInstanceFolder=<an empty temp directory>/`. The csproj copies the built DLL into the live game's Mods folder after every build; the `-p:ModInstanceFolder=...` override sends it to the temp directory instead. Do NOT run `task mod:build`, `task mod:deploy` or `task check`, because they deploy into the live game.
- Run `task lint` and `task scripts:test` before finishing; both are quick and must pass.
- Do not start the game, and do not run `uv run scripts/run.py` commands.

Steps (TDD): 1) write failing xUnit tests for `InjectedInputQueue` in `tests/MegabonkLevels.Tests/injected_input_tests.cs`: tap timing with and without modifiers, pressed/released last one frame, held persists, click timing, text one char per frame including backspace and return, mouse position persists and `ClearMouse` resets, repeated `BeginFrame` is a no-op, an unknown key name still queues (validation belongs to TASK-010.03); run them and confirm they fail; 2) implement the queue until they pass; 3) implement `EditorInput` and swap the call sites, compiling with the redirected build command above after each file; 4) run the verification commands above; 5) document the seam in docs/development.md (what it is, the frame semantics, where `EditorInput` is called), describing the content, not this task.

Done check: `rg 'Input\.(GetKey|GetMouse|mousePosition|inputString|GetAxis|mouseScrollDelta)' src` returns matches only inside editor_input.cs.

Left for a human, not this task's agent: confirming in the running game that the real keyboard and mouse still drive the editor exactly as before (palette clicks, W/A/S/D fly, tool hotkeys, R rotation, typing). Write that down in the task notes as an open item; do not claim it is verified.

Do not: add harness commands (TASK-010.03), touch the game's Rewired input, change editor behaviour, or edit the repo's own gating tooling (taskfiles, lint config, the test project beyond the one Compile Include line).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 InjectedInputQueue exists as a Unity-free class with the documented API and frame semantics, linked into the test project
- [x] #2 EditorInput returns the real UnityEngine.Input value or the injected one for key, mouse button, mouse position and input string reads, and passes axis and scroll reads through, using the same Input member for each call site as before
- [x] #3 EditorInput.Queue.BeginFrame(Time.frameCount) runs at the top of OnUpdate before the harness poll and any editor code
- [x] #4 A raw-Input search over src (rg 'Input\.(GetKey|GetMouse|mousePosition|inputString|GetAxis|mouseScrollDelta)' src) finds matches only in editor_input.cs, and the mod project compiles with the deploy redirected to a temp directory
- [x] #5 Queue behaviour (tap timing, pressed/released one frame, hold, click, text with backspace and return, mouse persistence and clear, repeated BeginFrame) has xUnit tests written first and passing
- [x] #6 docs/development.md describes the seam and its frame semantics
- [x] #7 The task notes list the in-game check that real keyboard and mouse input still behaves as before as an open item for a human, not as verified
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Definition of Done item 'task check passes' cannot be run unattended because task check builds the mod and the csproj deploys into the live game's Mods folder. Satisfy it by running its parts: task mod:test, the dotnet build with -p:ModInstanceFolder redirected to a temp directory, task lint and task scripts:test.

Open item for a human: confirm in the running game that the real keyboard and mouse still drive the editor exactly as before (palette clicks, W/A/S/D fly, tool hotkeys, R rotation, typing). Not verified; the game was not run. The task's rg done-check also matches 'EditorInput.' call sites because 'Input\.' is a substring; the check 'rg -P (?<![A-Za-z])Input\.(GetKey|GetMouse|mousePosition|inputString|GetAxis|mouseScrollDelta) src' finds matches only in editor_input.cs.
<!-- SECTION:NOTES:END -->
