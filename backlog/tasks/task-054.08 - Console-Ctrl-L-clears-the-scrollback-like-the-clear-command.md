---
id: TASK-054.08
title: Console Ctrl-L clears the scrollback like the clear command
status: To Do
assignee: []
created_date: '2026-11-08T17:01:00Z'
updated_date: '2026-11-08T17:02:00Z'
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
- [ ] #1 Ctrl-L clears the scrollback through the same path as the `clear` verb, including the persisted scrollback
- [ ] #2 Command history is unchanged: Up/Down and Ctrl-R still recall earlier entries, in the same session and after a restart
- [ ] #3 The input line and caret are unchanged and Ctrl-L adds no history entry
- [ ] #4 Ctrl-L does not type a character into the input line
- [ ] #5 Confirmed in the running game by harness screenshot
- [ ] #6 Binding documented in docs/development.md under the console overlay section
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
