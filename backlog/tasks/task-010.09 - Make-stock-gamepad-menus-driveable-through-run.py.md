---
id: TASK-010.09
title: Make stock gamepad menus driveable through run.py
status: Done
assignee: []
created_date: '2026-10-31T17:53:00Z'
updated_date: '2026-10-31T18:12:00Z'
labels: []
dependencies: []
parent_task_id: TASK-010
type: enhancement
ordinal: 131000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Stock Rewired/gamepadui menus cannot be driven by the editor's injected input. Recent wm2 verification required gitignored wm2_menu.py and an ad hoc virtual-input server with machine-specific paths, making the successful workflow unavailable to future agents. Promote that proven workflow into the maintained CLI without changing existing editor-input commands.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 run.py can drive validated keyboard, mouse and controller menu batches locally on Linux and through an explicitly configured SSH host, without machine-specific paths.
- [x] #2 Virtual input devices persist between batches and have explicit start/status/stop lifecycle; malformed input and device/display/SSH failures fail clearly without silently continuing.
- [x] #3 Menu batches can include harness diagnostics and capture a valid screenshot locally, including download from an SSH target; rejected/timed-out commands fail the batch.
- [x] #4 Tests cover validation, input release/cleanup, lifecycle, remote quoting/failure propagation and screenshot completion; documentation explains setup, permissions, display selection and cleanup.
- [x] #5 The maintained CLI is exercised on wm2 through stock menus, with virtual inputs cleaned up afterward.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add failing tests for a maintained `run.py menu` CLI: explicit persistent input-service start/status/stop, validated batches, optional screenshots/diagnostics, and configurable SSH forwarding. Preserve existing injected editor key/mouse commands.
2. Keep menu orchestration in run.py and isolate Linux uinput/X11 device mechanics in scripts/menu_input.py, imported lazily. Use a private per-user Unix socket, bounded JSON protocol, explicit virtual-controller opt-out, safe release/cleanup and actionable errors; no sudo or automatic permission changes.
3. Support configurable remote repository/interpreter/game path/display instead of wm2 constants. Send batch JSON through stdin, shell-quote only explicit command arguments, propagate nonzero exits, and download screenshots only after harness completion plus PNG validation.
4. Add Linux-only evdev dependency to both project and standalone script metadata, document commands and cleanup in development docs/AGENTS guidance, and exercise stock menu navigation plus screenshots on wm2. Run targeted and full local checks; retain the unrelated Linux THPS fixture-casing limitation.

Live findings incorporated: use a transient systemd user service on wm2 to outlive SSH logout and explicitly clean its named unit on uncertain startup; send a small genuine evdev mouse-motion pulse between absolute X11 warps so Rewired switches input modes. All acceptance criteria verified. Finish conventional commits and sync the maintained files to the target checkout.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Initial tests observed red before implementation (missing maintained menu module); subsequent lifecycle/validation/socket tests passed. Live SSH testing found detached child processes were reaped after SSH logout on wm2, so start now uses a transient systemd user service when available, with owned-unit cleanup on startup failure (and a detached-process fallback on non-systemd hosts). Status from a separate SSH invocation confirms the devices persist.

Live maintained CLI drove Enter + controller A from main menu through character selection into Map Selection and downloaded a completed PNG. Mouse testing found Rewired needs a genuine evdev motion event to switch away from controller input: X11 warp alone was insufficient. Added a red test, then a small real mouse-motion pulse between absolute warps; the maintained CLI now selects Warehouse by mouse and query-objects confirms only Tier 1 available/selected. No scratch input server or wrapper used for these checks.

Final maintained CLI live verification passed on wm2: persistent start/status across separate SSH calls; Enter + controller A reached stock Map Selection; a D-pad Down pulse focused Challenges; absolute mouse click selected Warehouse and a read-only query showed only Tier 1 selectable/selected. Switching from virtual controller back to mouse selected Forest and restored all three tier availabilities. Valid screenshots were captured/downloaded into local .tools/menu-proof-*.png, with unique remote evidence paths printed. Final lifecycle smoke on the latest code also passed. stop removed its socket and transient user service; game quit and harness marker restored disabled. Scratch .tools/wm2_menu.py and wm2_input.py retired.

51 new tests pass locally and on wm2. Final local task check passes: 1498 C# tests, 900 Python tests, build and lint. A broader wm2 run including tests/test_run.py had 271/273 pass at that point (before two final new tests were added): two existing Wine-exit tests attempt an unmocked kill of PID 7 and fail with PermissionError on Linux; this unrelated issue was left unchanged, and no elevated test run was attempted. The earlier unrelated THPS case-sensitive fixture issue was not changed either.

Documentation and AGENTS.md explain start/status/drive/stop, JSON batch schema, @file/stdin, remote repo/interpreter/game/display options, uinput permissions, systemd/foreground fallback, controller opt-out, screenshot completion/download behavior, device-motion mode switching and cleanup. Linux-only evdev added to pyproject/uv.lock and standalone run.py metadata; no automatic sudo, permission changes or remote dependency installation.

Implementation committed as cbec10c (feat: drive stock gamepad menus through run.py).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Promoted the scratch workflow into `run.py menu start|status|drive|stop`, backed by a maintained Linux uinput/X11 helper. Supports persistent virtual keyboard/mouse/Xbox input, validated JSON batches (@file/stdin), read-only harness diagnostics, screenshot completion and SSH download, configurable target paths/interpreter/display, private socket lifecycle and safe input release/cleanup. On systemd hosts, transient user services keep devices alive after SSH logout; mouse movement includes a genuine device pulse so Rewired switches out of controller mode. Existing editor input commands are unchanged.

Added Linux-only evdev dependency, 51 tests and discoverable docs/AGENTS guidance. Retired the scratch scripts. Implementation: cbec10c.

Verified stock menu keyboard/controller/mouse operation, diagnostics, PNG download and service cleanup on wm2. All 51 new tests pass on macOS and wm2. Local task check passes (1498 C# + 900 Python tests, build and lint). Two unrelated existing Wine-exit Python tests fail on Linux due to an unmocked PID-7 kill; documented in notes, not changed. Game stopped, harness disabled, input socket removed and transient service gone after testing.
<!-- SECTION:FINAL_SUMMARY:END -->
