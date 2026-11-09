---
id: TASK-061
title: Keep a console run.freeze frozen after the console closes
status: To Do
assignee: []
created_date: '2026-11-09T19:57:00Z'
labels: []
dependencies: []
references:
  - src/MegabonkLevels.Mod/console_overlay.cs
  - src/MegabonkLevels.Mod/console_state.cs
  - src/MegabonkLevels.Mod/console_command_registry.cs
  - src/MegabonkLevels.Mod/dev_harness.cs
documentation:
  - docs/development.md
priority: medium
type: bug
ordinal: 212000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Typing run.freeze in the in-game console prints ok but the run resumes the moment the console closes, so it cannot be used to hold a still scene. Opening the console already pauses a live run, which makes the verb a no-op, and closing it unpauses the run because it was not paused on entry. run.resume has the mirror problem: it unpauses while the console is open, but the console's remembered entry state is not updated. The MCP freeze tool sends the same harness command and is not affected when the console is closed, so this is a console-only interaction, not a regression from the MCP refactor. Console log evidence: "Console: opened, MyTime.paused=True", "DevHarness: freeze, MyTime.paused=True", "Console: closed, MyTime.paused=False".
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 After run.freeze is typed in the console and the console is closed, the run stays paused (MyTime.paused is true and the log shows no unpause on close).
- [ ] #2 After run.resume is typed in the console and the console is closed, the run is running and stays running.
- [ ] #3 A run frozen before the console opens, such as in the editor or by the death screen, is still left as it was on close.
- [ ] #4 The decision is covered by a test written first against the console state logic.
- [ ] #5 docs/development.md describes how console freeze and resume interact with the console's own pause on open and close.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
