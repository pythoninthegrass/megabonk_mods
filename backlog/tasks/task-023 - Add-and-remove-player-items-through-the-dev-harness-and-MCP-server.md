---
id: TASK-023
title: Add and remove player items through the dev harness and MCP server
status: To Do
assignee: []
created_date: '2026-10-28T20:30:00Z'
labels:
  - dev-harness
  - mcp
dependencies: []
documentation:
  - docs/development.md
priority: medium
type: feature
ordinal: 108000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Agents testing the game through the MCP server cannot change what the player holds. The only inventory control is the `invulnerable` switch, which hands the player 20 Mirrors (no cooldown) and 2 Feathers, so checking what happens when the player dies, or testing any item-dependent behaviour, means relaunching. The existing `vulnerable` switch is also broken: after `invulnerable` then `vulnerable` the harness logs `Mirror amount=19, Feathers amount=1`, so the player stays effectively unkillable and the run cannot be repaired without a relaunch, while docs/development.md says both items are removed. The wire format, `run.py` subcommands and MCP tools are described in docs/development.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Through the MCP server and run.py, an agent can read the player's current amount of a named game item
- [ ] #2 Through the MCP server and run.py, an agent can set the player's amount of a named item to an exact number, where 0 removes it
- [ ] #3 The result reports the item's amount before and after the change
- [ ] #4 An unknown item name, or a negative or unreasonably large amount, is rejected with a clear error and changes nothing and does not crash the game
- [ ] #5 After `invulnerable` then `vulnerable`, the player holds exactly the Mirror and Feathers amounts they had before `invulnerable`, verified in game
- [ ] #6 Command parsing is covered by C# tests and the run.py and MCP command building by Python tests, written before the implementation
- [ ] #7 The new command and MCP tool are verified in game through the MCP server, including setting an amount to 0 on a held item
- [ ] #8 docs/development.md documents the command, the run.py subcommand and the MCP tool, and its description of `invulnerable` and `vulnerable` matches the behaviour
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
