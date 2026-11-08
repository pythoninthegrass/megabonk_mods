---
id: TASK-054.11
title: Console replies show Windows paths with backslashes intact
status: To Do
assignee: []
created_date: '2026-11-08T20:05:00Z'
updated_date: '2026-11-08T20:05:00Z'
labels: []
dependencies: []
references:
  - src/MegabonkLevels.Mod/console_state.cs
  - src/MegabonkLevels.Mod/dev_harness.cs
documentation:
  - docs/development.md
parent_task_id: TASK-054
priority: low
type: bug
ordinal: 202000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A console reply that contains a Windows path with backslashes prints garbled. After `debug.screenshot tony.png` under Wine on macOS the reply should read `screenshot: Z:\<repo>\.tools\evidence\tony.png`, but the `\t` where the folder meets a file name starting with `t` is lost or shown as a tab, so the console prints `evidenceony.png` or `evidence     ony.png` instead of `evidence\tony.png`. Latest.log records the correct path, so the file lands in the right place and only the text the console shows is wrong. The reply is the main way to learn where a screenshot or saved level went, so a garbled path defeats it. Other replies that carry a path or any backslash (for example a saved-level path) are likely affected the same way but have not been checked.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A console reply containing a backslash path (for example the debug.screenshot reply for a relative name) prints the path exactly as the game wrote it, with no characters dropped and no tab inserted
- [ ] #2 Any other console reply that carries a path or backslash text is checked, and each affected one is fixed or recorded as unaffected
- [ ] #3 A test written first reproduces the garbled reply and fails before the fix
- [ ] #4 Verified in the running game by running debug.screenshot with a relative name and reading the printed path against Latest.log
- [ ] #5 docs/development.md notes the behavior if it changes how results are reported
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
