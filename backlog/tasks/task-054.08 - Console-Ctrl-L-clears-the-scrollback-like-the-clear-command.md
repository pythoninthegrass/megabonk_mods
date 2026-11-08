---
id: TASK-054.08
title: Console Ctrl-L clears the scrollback like the clear command
status: Done
assignee: []
created_date: '2026-11-08T17:01:00Z'
updated_date: '2026-11-08T17:05:00Z'
labels: []
dependencies: []
references:
  - src/MegabonkLevels.Mod/console_overlay.cs
  - src/MegabonkLevels.Mod/console_state.cs
documentation:
  - docs/development.md
parent_task_id: TASK-054
priority: low
type: feature
ordinal: 199000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Map Ctrl-L in the in-game console to the `clear` verb, as in a shell. It clears only the scrollback, including the persisted scrollback in `console_log.jsonl`, the same way typing `clear` does (via the existing bind and plan path). The command history (Up/Down recall, Ctrl-R finder, and the history restored from `console_log.jsonl`) stays intact. The input line and caret are untouched and Ctrl-L itself is not recorded in history. Letters typed while Ctrl is held are already dropped in `ConsoleOverlay.ReadInput`, so the chord does not type an `l`. Ctrl-L inside the Ctrl-R finder is out of scope unless trivial. Document the binding under "Console overlay" in docs/development.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Ctrl-L clears the scrollback through the same path as the `clear` verb, including the persisted scrollback
- [x] #2 Command history is unchanged: Up/Down and Ctrl-R still recall earlier entries, in the same session and after a restart
- [x] #3 The input line and caret are unchanged and Ctrl-L adds no history entry
- [x] #4 Ctrl-L does not type a character into the input line
- [x] #5 Confirmed in the running game by harness screenshot
- [x] #6 Binding documented in docs/development.md under the console overlay section
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
1. Add a test pinning that the registry's `clear` bind plans a scrollback clear with no harness command.
2. In console_overlay.cs extract PlanLine and ClearScrollbackAndStore from Submit; add ClearScrollbackChord (plans "clear", applies only the clear) and an `else if (CtrlHeld() && L)` branch after the Ctrl-R branch. The finder branch precedes it, so Ctrl-L is ignored inside the finder.
3. Document the binding in the console keys paragraph of docs/development.md.
4. task check, then relaunch and verify Ctrl-L with a harness screenshot.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Ctrl-L in the console runs the `clear` verb's plan through the same bind and plan path as typing `clear`, clearing the scrollback and appending the `clear` marker to console_log.jsonl. The input line, caret and history are untouched and nothing is recorded in history. Submit now shares PlanLine and ClearScrollbackAndStore with the chord. Verified in the running game: after `state` and the half-typed text `half typed`, Ctrl-L emptied the scrollback and kept the input unchanged with no `l` typed; Up then recalled `state`; the log ends with the `in state` and `clear` entries and no entry for the chord. History surviving a restart after a clear is covered by the existing store test `Load_ClearMarkerDropsEarlierScrollbackButKeepsHistory`. Unit test added for the registry's `clear` bind. task check, mod:test and the Python suite pass. Docs: console keys paragraph in docs/development.md.
<!-- SECTION:FINAL_SUMMARY:END -->
