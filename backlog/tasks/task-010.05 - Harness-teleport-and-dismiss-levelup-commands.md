---
id: TASK-010.05
title: Harness teleport and dismiss-levelup commands
status: To Do
assignee: []
created_date: '2026-10-22 03:43'
labels:
  - dev-harness
  - tooling
dependencies:
  - TASK-010.01
  - TASK-010.04
references:
  - scripts/run.py
  - tests/test_run.py
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/harness_command.cs
  - tests/MegabonkLevels.Tests/harness_command_tests.cs
documentation:
  - docs/development.md
  - AGENTS.md
parent_task_id: TASK-010
priority: medium
ordinal: 58000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-010 first. Depends on TASK-010.01 (result files and the `Execute` return value) and TASK-010.04 (docs/development.md sections that record how to teleport the player and how to dismiss the level-up dialog, with classes, methods and the confirmed call sequence). Do not start until both are done; implement exactly what TASK-010.04 documented. If TASK-010.04 recorded either question as unanswered, implement only the answered one and tell Lance. Can run in parallel with TASK-010.03 and TASK-010.06.

Goal: let an agent move the player and clear the level-up dialog so a run can be walked and tested (TASK-004 AC#3 enemy pathing, TASK-005.06 playtest) without keyboard or mouse input.

Wire formats (decided):
- `{"command":"teleport","position":[x,y,z]}` or `{"command":"teleport","cell":[cx,cy]}`; exactly one of the two. A cell is converted to a world position at the cell centre using the existing grid conversion (see `position_cell_centre_tests.cs` and its source for the tested helper, and read tile spacing from the running stage, never hardcode it); the height is the tile's surface at that cell, falling back to the player's current height when the cell is empty. The result is `{"position":[x,y,z],"cell":[cx,cy]}` with the position actually reached.
- `{"command":"dismiss-levelup","choice":0}`; `choice` is an optional zero-based index into the offered upgrades (default 0). The result is `{"dialogWasOpen":true|false,"chosen":"<upgrade name or null>"}`. When no dialog is open, the command succeeds with `dialogWasOpen:false` and does nothing.
- A request that cannot be honoured (no run active, no player, choice out of range, both or neither of position/cell) is rejected: parse errors at parse time, runtime failures by throwing from `Execute` so TASK-010.01's result file reports `ok:false` with the message.

Steps (TDD): 1) failing xUnit tests in harness_command_tests.cs for `TryParse` of both commands (valid forms, both/neither of position/cell, wrong array lengths, negative choice) and for any pure cell-to-position helper you add (reuse the existing one first; do not duplicate it); 2) failing Python tests in tests/test_run.py for the `teleport` and `dismiss-levelup` subcommand payloads; 3) add `Teleport` and `DismissLevelUp` to `HarnessCommandKind`, `TryParse` and `Execute` using the TASK-010.04 call sequence; 4) run.py: `teleport X Y Z`, `teleport --cell CX CY`, `dismiss-levelup [--choice N]`, each printing the result JSON; update the docstring usage; 5) `task check`; 6) in the game: relaunch, `invulnerable`, `teleport --cell` to a distant cell and confirm with `state` (TASK-010.01) and a screenshot; wait for or force a level-up and confirm `dismiss-levelup` clears it; 7) docs/development.md: document the commands, wire formats and results next to the TASK-010.04 findings, and remove "move the player" and "skip the level-up dialog" from the Not covered list.

Do not: re-research the game internals (use the TASK-010.04 findings, and if they are wrong or incomplete, record the correction in the same docs section), or bypass the kill floor or invulnerability behaviour.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 teleport accepts exactly one of position or cell, moves the player there in the running game, and returns the position and cell actually reached
- [ ] #2 dismiss-levelup applies the chosen upgrade when the dialog is open and returns dialogWasOpen and chosen, and succeeds with dialogWasOpen false and no effect when no dialog is open
- [ ] #3 Invalid or impossible requests (no run, no player, bad choice, both or neither of position/cell) are rejected with a clear error visible in the result file
- [ ] #4 run.py has teleport and dismiss-levelup subcommands that build the documented payloads and print the result JSON
- [ ] #5 Confirmed in the running game: a teleport to a distant cell shows in state and in a screenshot, and a level-up dialog is cleared by dismiss-levelup
- [ ] #6 Parsing, validation and any pure helper logic have tests written first, and an existing cell-to-position helper is reused rather than duplicated
- [ ] #7 docs/development.md documents both commands and the Not covered list no longer lists moving the player or skipping the level-up dialog
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
