---
id: TASK-032.08
title: >-
  Harness verbs to press the death screen's Confirm and the run summary's
  Restart
status: Done
assignee: []
created_date: '2026-11-05T20:34:00Z'
updated_date: '2026-11-05 20:52'
labels: []
dependencies: []
references:
  - >-
    backlog/tasks/task-032.07 -
    Verify-from-scratch-levels-end-to-end-in-the-running-game.md
  - docs/development.md
parent_task_id: TASK-032
priority: medium
ordinal: 167000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Checking a death-screen restart in the running game currently needs a person at the keyboard. The harness injects mouse and key input for the editor only, and `click_widget` and `ui_tree` refuse outside editor mode, so an agent cannot press Confirm on the "you ded" screen or the Restart button on the run-summary screen that follows it. `restart_run` skips both screens by calling `MapController.RestartRun` directly, so it does not prove the player-facing path works. This blocked the death-and-retry check in TASK-032.07, and the same gap affects any future restart regression check on custom levels. On macOS under Wine, OS-level input (osascript) is the only workaround and takes over the host desktop.

Context for a worker with no memory of the discussion: the death screen shows Confirm, which opens a run-summary window with a Restart button. `docs/development.md` ("Death screen restart") currently says the summary window's retry is `B_Retry` and that `B_Restart` is a different button not to be read as the death screen's; the maintainer states the summary screen has a "restart" button, so that doc passage should be checked against the game and corrected if wrong.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A harness command and matching MCP tool press Confirm on the death screen and report whether it was open, in the style of the existing dismiss-offers result
- [x] #2 A harness command and matching MCP tool press the run summary screen's Restart button and report which button was pressed
- [x] #3 Both fail with a clear error, without side effects, when the corresponding screen is not showing
- [x] #4 After the Restart press on a from-scratch custom level, the log shows the custom run restarting and the player is at the authored spawn
- [x] #5 docs/development.md documents both verbs, and its death-screen section names the button the summary screen actually shows
- [x] #6 Unit tests for the command parsing and any Unity-free decision logic are written first and pass; task check passes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first (harness_command_tests.cs, test_run.py, test_mcp_server.py) for commands press-death-confirm and press-summary-restart; confirm they fail.
2. Add HarnessCommandKind entries, parser cases, run.py builders/subparsers/dispatch, MCP tools press_death_confirm and press_summary_restart.
3. dev_harness.cs handlers: Confirm requires an active DeathScreen with deadUiWindow showing; Restart requires statsWindow active and the retry button active. Both throw a clear error without side effects otherwise, and refuse a non-interactable button. Invoke the game's own button handler (not a pointer click). Results report screenWasOpen and the button name.
4. Inspect the running game (kill, dump Confirm onClick targets and summary buttons B_Retry vs B_Restart); correct docs if wrong.
5. End-to-end check on levels/thps.mblevel.json: relaunch, kill, press confirm, press restart; log shows custom run restarting, player at authored spawn; both verbs error when screen not showing.
6. Update docs/development.md, task check, check ACs, conventional commit with no attribution.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added harness commands press-death-confirm and press-summary-restart (run.py subcommands, MCP tools press_death_confirm and press_summary_restart). Both call the button's own onClick via DeathScreenPress, gated by DeathScreenPressGate (unit-tested), and refuse with a clear error and no side effect when the screen is not showing or the button is inactive or non-interactable. Results are {screenWasOpen, button, label}. Live check on levels/thps.mblevel.json: kill, confirm (B_Continue, "Confirm"), restart (B_Retry, label "Restart"); log shows the custom run restarting and the player placed at the authored start. docs/development.md documents both verbs and the button names; B_Retry is the summary's Restart, B_Restart is a separate scene object.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
