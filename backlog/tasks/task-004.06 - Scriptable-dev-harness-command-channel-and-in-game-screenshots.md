---
id: TASK-004.06
title: 'Scriptable dev harness: command channel and in-game screenshots'
status: In Progress
assignee:
  - Claude
created_date: '2026-10-08 02:13'
updated_date: '2026-10-08 02:36'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-004
priority: medium
ordinal: 37000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Right now, exercising the mod in the running game means pressing F6 and driving menus with OS-level key presses (osascript on macOS, a KVM on the Linux host). That was unreliable in TASK-004.02: the idle player died within about 20 seconds, the level-up dialog blocked input, there was no mouse input, and screenshots came from the host screen rather than the game. Add a small development-only harness inside the MelonLoader mod so a shell script can run a load-and-check cycle without simulating input: trigger a level load, capture the game's own frame, and quit. Read docs/level-format.md (runtime playback section) and docs/modding-setup.md first; the mod already loads a level and applies its edits when F6 is pressed.

Open design choices to settle during planning, not here: file-drop watcher versus localhost listener, and how the harness is enabled (env var versus config file). Under Wine/CrossOver, localhost networking and ScreenCapture.CaptureScreenshot are untested; confirm both before committing to them.

Out of scope, deliberately deferred to a future task because each needs reverse-engineering of game internals that has not been done: making the player invulnerable, skipping the level-up dialog, moving the player/camera, and invoking menu buttons programmatically.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A script outside the game can trigger loading a given level file without a keypress and without the file having a hardcoded name, and the run starts with its edits applied
- [x] #2 A script can request a screenshot of the game's own rendered frame to a chosen path, and the file is a valid image of the running scene
- [x] #3 A script can request that the game quit cleanly, and the log records that it did
- [x] #4 An unrecognised or malformed command logs a clear warning and does not crash or change game state
- [x] #5 The harness is off by default, so a normal player install exposes no command channel unless it is explicitly enabled
- [x] #6 Verified end to end on the macOS/CrossOver install: launch, load a level, take a screenshot, quit, all from the shell with no osascript key presses after launch
- [x] #7 Pure command parsing is unit tested, with the tests written before the implementation
- [x] #8 The commands, how to enable the harness, and any Wine/CrossOver caveats are documented
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Transport: file-drop watcher. scripts/run.py writes one JSON command file per command into <game dir>/harness/commands/; the mod polls it in OnUpdate, runs each command, then moves the file to harness/done/ or harness/rejected/.
2. Enable: marker file <game dir>/harness/enabled (config lives in the game dir). No marker, no polling, no channel (AC5). run.py enable/disable create and remove it.
3. Commands (JSON): load-level {path} (any path, reuses LevelLoaderPatch.LoadAndStart), screenshot {path} (ScreenCapture.CaptureScreenshot), quit (log, then Application.Quit). Unknown or malformed commands log a warning, go to rejected/, and change no state (AC4).
4. Mod side, TDD: failing xUnit tests for a pure HarnessCommand.Parse first (tests/MegabonkLevels.Tests/harness_command_tests.cs), then src/MegabonkLevels.Mod/harness_command.cs, then a thin dev_harness.cs (poll, dispatch, log) and an OnUpdate hook in megabonk_levels_mod.cs.
5. scripts/run.py replaces the boilerplate: keeps the PEP 723 header with python-decouple (drops httpx and sh), self-contained, resolves the game dir from process env vars then a relative .env (MEGABONK_GAME_DIR, MEGABONK_BOTTLE, same precedence as game_paths.py). Subcommands: enable, disable, load <level>, screenshot <out>, quit, cycle <level> <out>. Waits for done/rejected with a timeout and reports via exit code. Pure functions self-tested in scripts/test_run.py.
6. Consolidate tools/ into scripts/ (git mv tools/*.py scripts/) and update every reference (taskfiles, taskfile.yml, docs, README, AGENTS.md, .env.example, ruff/lint paths).
7. Docs: new docs/development.md (commands, enabling, Wine/CrossOver caveats); link from docs/modding-setup.md; add a task game:harness entry.
8. Verify: confirm CaptureScreenshot works under CrossOver before relying on it, then run the end-to-end cycle on the macOS install (AC6).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified on macOS/CrossOver by launching Megabonk.exe directly in the Steam bottle with SteamAppId set: cycle (load, screenshot, quit) exits 0, the PNG is a valid 2560x1440 frame of the forest level, quit is logged, bad/unknown/path-less commands are rejected with warnings, and the 2-edit test level logs 'LiveEdit: applied 2 edit(s)'. ScreenCapture.CaptureScreenshot and ImageConversion.EncodeToPNG fail in Il2CppInterop, so screenshots use Texture2D.ReadPixels plus a managed PNG encoder. Scripts moved from tools/ into scripts/ at the user's request.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
