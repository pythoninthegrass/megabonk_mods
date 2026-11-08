---
id: TASK-054.05
title: Drive the in-game console from run.py and the MCP server
status: To Do
assignee: []
created_date: '2026-11-08T07:54:00Z'
labels: []
dependencies:
  - TASK-054.01
  - TASK-054.02
references:
  - scripts/run.py
  - scripts/mcp_server.py
  - src/MegabonkLevels.Mod/harness_command.cs
  - src/MegabonkLevels.Mod/dev_harness.cs
  - tests/test_mcp_server.py
documentation:
  - docs/development.md
parent_task_id: TASK-054
priority: medium
type: enhancement
ordinal: 196000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Agents verify game changes through the dev harness (`scripts/run.py` and the `megabonk` MCP server), not through OS-level keyboard input. Typing into the console with the harness `type` and `key` commands works, but it is slow, depends on the overlay being open, and gives back only a screenshot. A harness command that takes a raw console line and returns the console's reply lines makes the command language (TASK-054.02) testable end to end on any fleet box, including headless SSH sessions. The reply is exactly what the overlay would print. Lines run this way also appear in the console's scrollback and history, so a later screenshot shows them.

The line goes through the same registry, gating and dispatch as typed input, so `MEGABONK_DEV` gating applies here too.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A harness command accepts a console line and returns its reply lines and an ok flag; parse tests cover a missing or empty line
- [ ] #2 run.py gains a console subcommand taking the line as one argument, printing the reply
- [ ] #3 The MCP server gains a console tool returning the reply; tests/test_mcp_server.py covers the payload
- [ ] #4 Gated verbs sent this way reply 'requires MEGABONK_DEV' when MEGABONK_DEV is not true
- [ ] #5 Lines run through the harness appear in the overlay's scrollback and history
- [ ] #6 docs/development.md lists the run.py and MCP console commands alongside the other harness commands
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
