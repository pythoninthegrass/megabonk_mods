---
id: TASK-061
title: Keep a console run.freeze frozen after the console closes
status: Done
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
- [x] #1 After run.freeze is typed in the console and the console is closed, the run stays paused (MyTime.paused is true and the log shows no unpause on close).
- [x] #2 After run.resume is typed in the console and the console is closed, the run is running and stays running.
- [x] #3 A run frozen before the console opens, such as in the editor or by the death screen, is still left as it was on close.
- [x] #4 The decision is covered by a test written first against the console state logic.
- [x] #5 docs/development.md describes how console freeze and resume interact with the console's own pause on open and close.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Notes

<!-- SECTION:NOTES:BEGIN -->
The close decision is a pure function in `ConsoleState` (`AfterFreeze`, `AfterResume`)
next to `ShouldUnpauseOnClose`; `ConsoleOverlay` updates its remembered `ConsoleEntryState`
only for a freeze or resume the console ran itself, so `run.py` and the MCP tools are
unaffected. Five tests were added to `console_state_tests.cs` before the implementation and
were confirmed to fail with `CS0117: 'ConsoleState' does not contain a definition for
'AfterFreeze'`/'AfterResume'` before the implementation was restored.

Verified with `task check` (build, installer tests, 2863 xUnit tests, 2784 Python tests,
markdownlint, ruff, deno fmt/lint) plus a focused `dotnet test` on `ConsoleStateTests`
(54 passed). The game itself was not run, so AC #1-#3 are verified at the decision layer and
by reading `CloseConsole`, not from a live session: the live check is to type `run.freeze`,
close the console and confirm the log prints `Console: closed, MyTime.paused=True`.

The C# language server in this session cannot resolve the test project's `xunit` package or
its `<Using Include="Xunit" />`, so it reports `Fact`/`Assert` missing on every test in the
file including pre-existing untouched ones, and reported `AfterFreeze` missing after it was
implemented. `dotnet build` and `dotnet test` compile and run the same file with no errors,
so those diagnostics are a stale server state, not a defect in the change; they were not
worked around and the repo's tooling was not modified.
<!-- SECTION:NOTES:END -->
