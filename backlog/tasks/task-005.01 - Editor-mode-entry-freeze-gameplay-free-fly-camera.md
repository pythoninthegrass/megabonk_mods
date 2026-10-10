---
id: TASK-005.01
title: 'Editor mode entry, freeze gameplay, free-fly camera'
status: In Progress
assignee:
  - '@Claude'
created_date: '2026-10-06 21:43'
updated_date: '2026-10-10 05:41'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-005
priority: high
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005 first for full context.

Implement entering/exiting an editor overlay mode via a keybind (e.g. F8, confirm it doesn't collide with an existing game binding via Rewired's input map). On entry: pause the stage timeline and enemy spawning, disable player control/damage, and switch the active camera to a free-fly camera (detached from the player, mouse-look + WASD + vertical movement) so the player can survey/navigate the whole map. On exit: restore the previous camera and gameplay state cleanly (no lingering paused state if the player exits without saving).

This subtask is pure mode-management plumbing — no editing tools yet (that's TASK-005.02-.04). Verify entering and exiting repeatedly doesn't leak state (e.g. multiple free-fly cameras stacking, gameplay staying paused after exit).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A keybind toggles editor mode on/off without colliding with existing game bindings
- [x] #2 Entering editor mode pauses the stage timeline, enemy spawning, and player control/damage
- [x] #3 Entering editor mode switches to a free-fly camera with mouse-look and WASD+vertical movement
- [x] #4 Exiting editor mode restores the prior camera and resumes gameplay cleanly, verified across multiple enter/exit cycles with no leaked state
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
## Decisions already made with Lance

- Keybind: **F8** (confirm empirically in-game; see research note below on why it can't be confirmed from code).
- Free-fly controls: **WASD + mouse-look, Space/Ctrl up-down, Shift to move fast**. Mouse-look on right-mouse-hold, so the cursor stays free for the palette UI that TASK-005.02 adds.
- Scope: editor mode opens in **any active run**, not only mod-loaded custom levels, so a level can be started from a vanilla-generated map.

## Research findings (complete — do not redo)

**There are no managed method bodies to decompile.** `MelonLoader/Il2CppAssemblies/*.dll` are Il2CppInterop proxies: every method is a `NativeMethodInfoPtr` thunk with no IL. Running ilspycmd on them yields only interop plumbing. Real behaviour is native code in `GameAssembly`. The managed-level source of truth is `.tools/il2cpp_dump/dump.cs` (fields + signatures only, no bodies, regenerate with `task re:dump`); anything needing an actual method body requires native RE in Binary Ninja.

What the dump plus already-verified live behaviour establishes:

- Input is Rewired through `MyInputManager` (dump.cs:333116), with a fixed static action list: `Jump`, `JumpBhop`, `Slide`, `Aim`, `Interact`, `QuickReset`, `MapOverlay`, `Wallrun`, `MoveHorizontal`/`MoveVertical`, `LookHorizontal`/`LookVertical`, and the `UI*` set. All gameplay actions, none plausibly bound to an F-key. The actual key-to-action bindings live in a Rewired ScriptableObject asset that Il2CppDumper does not emit, so **F8 being unbound has to be confirmed by pressing it in-game**, not read from code. Access is via `MyInputManager.GetButton/GetButtonDown/GetAxis(string action)` and `IsActionBound(string)`.
- `MyTime` (dump.cs:359927) owns `paused`, `stageTimer`, `runTimer`, `difficultyTimer`, `finalSwarmTimer`, `timeScale` and `A_Pause`. `MyTime.Pause()` is already proven live (docs/development.md, "Freezing gameplay") to stop the run timer, enemies and the player, so it covers AC #2 on its own — no separate spawner or `PlayerHealth` work needed.
- `PlayerCamera` (dump.cs:329906) exposes a single `Camera camera` plus a private `Update()`. `CameraOverride` already proves that rewriting `camera.transform` from `MelonMod.OnLateUpdate` beats the game's own update and held for 6+ seconds of live play. Free-fly therefore reuses that mechanism rather than spawning a second camera — which also means there is no camera to stack, removing one of the leak risks named in AC #4.
- `DebugConsole` (dump.cs:361058) has `IsActive()` and `Toggle()`; the game's own console is on F10, which is why the mod already avoids that key (mod currently owns F6 and F9).

## Implementation steps

1. **Tests first** for the two pure-logic pieces; confirm red before implementing.
2. `src/MegabonkLevels.Mod/free_fly_camera.cs` — `FreeFlyCamera.Step(CameraPose pose, FreeFlyInput input, float deltaSeconds, settings) -> CameraPose`. No Unity types, so it compiles into the test project like `kill_floor.cs`. Reuse the existing `CameraPose` record struct from `harness_command.cs` (Rx = pitch, Ry = yaw) so the result feeds `CameraOverride.Set` directly. Camera-relative forward/right, world-up vertical, pitch clamped to +/-89 degrees, yaw normalised into [0, 360), mouse delta applied *without* deltaTime scaling (frame-rate-independent look) while movement *is* deltaTime-scaled.
   Tests: forward at yaw 0 moves +Z and at yaw 90 moves +X; up input moves +Y regardless of pitch; pitch clamps at both extremes; yaw wraps; fast modifier multiplies distance; zero input leaves the pose unchanged.
3. `src/MegabonkLevels.Mod/editor_session_state.cs` — records what entry changed so exit restores exactly that. `Enter(bool gamePausedBefore)` returns false if already active; `TryExit(out bool shouldUnpause)` returns false if not active. The real defect this prevents: entering editor mode while the game is *already* paused (e.g. a level-up dialog is open) must NOT unpause the game on exit.
   Tests: enter twice is a no-op; exit without enter is a no-op; entered-while-running then exit unpauses; entered-while-already-paused then exit does not unpause; repeated enter/exit cycles keep the flag correct (this is the unit-level half of AC #4).
4. `src/MegabonkLevels.Mod/editor_mode.cs` — Unity glue, untested like the other glue files (`position_label.cs`, `kill_floor_watcher.cs`). Polls F8 in `OnUpdate`; ignores the key while `DebugConsole.Instance?.IsActive()` is true and while no run is active; calls `MyTime.Pause`/`Unpause` via `EditorSessionState`; seeds the free-fly pose from the current camera transform on entry; each frame reads legacy `UnityEngine.Input` into a `FreeFlyInput` and pushes `FreeFlyCamera.Step`'s result to `CameraOverride.Set`; calls `CameraOverride.Clear()` on exit. Wire into `MegabonkLevelsMod.OnUpdate`.
5. **Harness command** so enter/exit cycles are verifiable without a keyboard (the harness cannot press keys): add `HarnessCommandKind.Editor` parsed from `{"command":"editor","enabled":true}` exactly like `heartbeat`/`cells`, dispatch it in `dev_harness.cs`, and add `run.py editor <on|off>` with a matching case in `scripts/test_run.py`.
6. `task check` (build + xUnit + python self-tests + markdownlint + ruff).
7. **Live verification** on the CrossOver reference platform (see docs/development.md for launching): load `levels/task-004-05-regression.mblevel.json`, run at least 5 `editor on` / `editor off` cycles through the harness, screenshot in editor mode and after exit, and grep `MelonLoader/Latest.log` for `MyTime.paused` returning to false, the camera restored, and zero errors across the cycles. Then ask Lance to drive F8 + WASD + mouse-look manually once: that is the only way to close AC #1 (F8 collides with nothing) and AC #3 (the camera actually flies).
8. **Docs**: add the `editor` row to the harness command table in `docs/development.md` and an "Editor mode" section covering the keybind, what entry freezes, the free-fly controls, and what exit restores. Follow AGENTS.md "Writing docs/*.md" — document the behaviour, never cite TASK-### IDs.
9. Check acceptance criteria against the evidence, record implementation notes, conventional commit with no attribution.

## Contingencies to check live, not assume

- Whether the game's own mouse-look still rotates the player while `MyTime.paused` is true. If it does, disable the `PlayerInput` component for the duration of editor mode and restore it on exit.
- Cursor lock is deliberately **not** managed in this subtask. The game locks the cursor during gameplay and `Input.GetAxis("Mouse X"/"Mouse Y")` works fine locked; TASK-005.02's palette UI is what actually forces the cursor decision, so make it there.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented and verified in the running game; not yet committed.

Evidence per criterion:
- AC1: Lance pressed F8 in the game and it toggled editor mode with no side effects reported. This rests on his observation; a Rewired binding cannot be read from code.
- AC2: log shows `EditorMode: entered, MyTime.paused=True` on every entry, and Lance saw the player (Tony McZoom) stay frozen. Enemy spawning and enemy freeze rely on MyTime.Pause, which was proven separately for the harness freeze command; they were not re-observed inside editor mode.
- AC3: Lance flew the camera with WASD, Space/Ctrl, Shift and mouse-look.
- AC4: six harness `editor on`/`off` cycles on levels/task-004-05-regression.mblevel.json, all balanced with `MyTime.paused` True then False, zero errors in Latest.log, plus Lance's manual enter/exit cycles. The harness screenshots (in editor mode and after exit) show the same view because the free-fly pose seeds from the current camera, so they do not prove the restore by themselves.

Findings worth keeping:
- The game's own LookHorizontal/LookVertical Rewired axes read zero while paused, so look uses raw Unity Mouse X/Y.
- Measured with a temporary probe (removed): the player turns 1 degree per raw mouse unit at saved sensitivity 1.0, same sign convention. Look is scaled by SaveManager.Instance.config.cfControlSettings.sensitivity and the two inverted-axis flags. Lance confirmed the rate matches normal play.
- The player does not turn or move while paused, so no PlayerInput workaround is needed.
- Movement speed 60 units/s (4x with Shift) is a fixed choice; Lance confirmed it feels right.
- Launch workflow fixes made along the way: task game:run now starts cxstart detached via python subprocess (Task's built-in shell kills `&` children), sets SteamAppId/SteamGameId, and AGENTS.md has the reload order of operations.

Deviation: the run.py `editor` argument tests in scripts/test_run.py were written after the run.py change, not before. The C# logic tests were written first and confirmed red.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
