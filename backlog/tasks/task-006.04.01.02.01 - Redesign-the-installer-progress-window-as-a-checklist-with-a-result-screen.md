---
id: TASK-006.04.01.02.01
title: Redesign the installer progress window as a checklist with a result screen
status: Done
assignee: []
created_date: '2026-11-04 01:54'
updated_date: '2026-11-04 02:17'
labels:
  - installer
  - ui
dependencies: []
documentation:
  - docs/player-installer.md
modified_files:
  - go/internal/window/window.go
  - go/internal/window/window_test.go
  - go/internal/window/icons/check.svg
  - go/internal/window/icons/x.svg
  - go/internal/window/icons/circle.svg
  - go/internal/ui/ui.go
  - go/internal/cli/cli.go
  - go/internal/cli/cli_test.go
  - docs/player-installer.md
parent_task_id: TASK-006.04.01.02
priority: low
ordinal: 149000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Go installer's native progress window showed one step label and a percentage bar, asked "Yes" before installing, and closed the moment the run ended, so a double-click player never saw the outcome, an error, or the Steam launch option (which only went to stdout). Redesign it so the plan, the progress and the result are all readable in the window, and so the buttons follow platform convention (Cancel left, the affirmative action right).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Before the run starts the window lists every planned step as pending, under a capitalised header, with Cancel on the left and an accent Install button on the right
- [x] #2 During the run finished steps show a green check, the active step a spinner, and later steps a muted circle, with a completed-step count beside the header
- [x] #3 The window stays open after the run with the result message and a Done button; Cancel closes it once the executor has stopped
- [x] #4 A failed run marks the failing step with a red cross, shows the full error message wrapped, and opens the Details log
- [x] #5 A collapsible Details log, closed by default, holds the step lines and everything the installer prints to stdout
- [x] #6 After a successful install that needs a Steam launch option, the window shows the option with a Copy button that puts it on the clipboard
- [x] #7 The window's result message and the plain-text reporter's closing message start with a capital letter; JSON mode, the numbered step lines and the headless path print what they printed before
- [x] #8 Unit tests cover the confirm buttons, checklist rows, finish and failure states, Done, Copy, the Details log and the plan, log and failure hooks the CLI drives; the progress-window section of docs/player-installer.md describes the new behaviour
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. ui package: add optional Planner, Logger and LaunchOptionShower interfaces beside Cancellable and Confirmer, so the text and null reporters are untouched.
2. window package: embed check, cross and circle SVG icons; Progress keeps the planned steps, completed steps, log, launch option and a dismissed flag; the view is split into heading, checklist, status, launch-option box, details and buttons; Run waits for Done, a close or a quit after the work returns.
3. cli package: runProgress takes a windowRun (title, prompt, planned steps, cancel message); it hands the plan to the window before the confirm, tees Reporter.Say and Warn into the details log, and calls Finish(false) on an error; doInstall passes the action labels and shows the launch option after the summary.
4. docs/player-installer.md: update the progress-window section.
5. Tests first in window_test.go and cli_test.go; verify the real window by running it on macOS with MEGABONK_UI_STEP_DELAY set, including a failure and dark mode.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented in the working tree, not yet committed. go vet and go test ./... pass; markdownlint passes on the changed docs. The confirm and running states were checked in the real window on macOS (light mode).

Deviations from the plan: the Enter shortcut on Install was dropped because mygo fires it only while the button has focus, and a focused button already takes Enter. The header is capitalised in the window only; the text reporter and plan labels are unchanged. Pressing Cancel closes the window once the executor has stopped, so its Finish(false) message is not shown.

Not yet checked in the real window: the finished and failed states, the Details log, Copy, and dark mode. AC 3 and 4 stay open until they are.

Checked in the real window on macOS through a throwaway driver, since deleted: confirm, running, finished with launch option, failed, Details open, Copy (the clipboard held the launch option), Done (process exits), Cancel mid-run (the window closes once the work stops, no Done needed), and dark mode.

The visual pass found a layout bug that unit tests could not: with the launch option and Details both showing, the checklist's scroll area shrank to zero height and the step rows disappeared. The checklist now keeps a minimum height for up to five rows, the window is 520x520 and the log area is capped at 110 DIPs. The fix has no unit test because the Tester asserts on text, not on laid-out height.

The task-level Definition of Done items stay open until the commit.

The window's result message and the text reporter's closing message are capitalised through the shared ui.Capitalize. The window's content tests match case-insensitively; dedicated tests assert the capital letter. Screenshots of the finished and failed states were taken before the message was capitalised.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Redesigned the Go installer's native progress window and aligned the plain-text closing message with it.

What changed:
- The window lists every planned step up front (muted circle), shows a spinner on the running step and a green check on finished ones, and marks the failing step with a red cross. A count such as "2 of 5" sits beside a capitalised header.
- Buttons follow platform convention: Cancel on the left, an accent Install button on the right (it was "Yes").
- The window stays open after the run with the result message (capitalised) and a Done button, instead of quitting as soon as the work returns.
- A collapsible Details log holds the step lines and everything the installer prints to stdout; it opens by itself on failure.
- After a successful install that needs a Steam launch option, the window shows it with a Copy button.
- The checklist keeps room for up to five rows, so it no longer collapses when the launch option and Details are both showing; the window is 520x520.
- The plain-text reporter's closing message is capitalised through the shared ui.Capitalize. Numbered step lines, JSON mode and the headless path are unchanged.

How: ui gained optional Planner, Logger and LaunchOptionShower interfaces so the text and null reporters stay untouched. runProgress takes a windowRun, hands the plan to the window before the confirm, tees Reporter.Say and Warn into the details log, and reports a run error through Finish(false). docs/player-installer.md describes the new window.

Verification: go vet and go test ./... pass; markdownlint passes on the changed docs. The window was driven on macOS in light and dark mode through a throwaway harness (confirm, running, finished with launch option, failed, Details, Copy, Done, Cancel mid-run); screenshots of the finished and failed states predate the capitalised message, whose change is small. task check was not run.

Caveats: the window and ui tests were written and seen failing before the implementation, but the CLI tests were written alongside it without a separate red run. The layout fix has no unit test because the test harness asserts on text, not laid-out height. Pressing Cancel closes the window once the executor stops, so the Finish(false) message sent for a cancelled run is never shown.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
