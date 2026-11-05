---
id: TASK-032.08
title: >-
  Harness verbs to press the death screen's Confirm and the run summary's
  Restart
status: To Do
assignee: []
created_date: '2026-11-05T20:34:00Z'
labels: []
dependencies: []
references:
  - >-
    backlog/tasks/task-032.07 -
    Verify-from-scratch-levels-end-to-end-in-the-running-game.md
  - docs/development.md
parent_task_id: TASK-032
priority: medium
type: enhancement
ordinal: 167000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Checking a death-screen restart in the running game currently needs a person at the keyboard. The harness injects mouse and key input for the editor only, and `click_widget` and `ui_tree` refuse outside editor mode, so an agent cannot press Confirm on the "you ded" screen or the Restart button on the run-summary screen that follows it. `restart_run` skips both screens by calling `MapController.RestartRun` directly, so it does not prove the player-facing path works. This blocked the death-and-retry check in TASK-032.07, and the same gap affects any future restart regression check on custom levels. On macOS under Wine, OS-level input (osascript) is the only workaround and takes over the host desktop.

Context for a worker with no memory of the discussion: the death screen shows Confirm, which opens a run-summary window with a Restart button. `docs/development.md` ("Death screen restart") currently says the summary window's retry is `B_Retry` and that `B_Restart` is a different button not to be read as the death screen's; the maintainer states the summary screen has a "restart" button, so that doc passage should be checked against the game and corrected if wrong.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A harness command and matching MCP tool press Confirm on the death screen and report whether it was open, in the style of the existing dismiss-offers result
- [ ] #2 A harness command and matching MCP tool press the run summary screen's Restart button and report which button was pressed
- [ ] #3 Both fail with a clear error, without side effects, when the corresponding screen is not showing
- [ ] #4 After the Restart press on a from-scratch custom level, the log shows the custom run restarting and the player is at the authored spawn
- [ ] #5 docs/development.md documents both verbs, and its death-screen section names the button the summary screen actually shows
- [ ] #6 Unit tests for the command parsing and any Unity-free decision logic are written first and pass; task check passes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
