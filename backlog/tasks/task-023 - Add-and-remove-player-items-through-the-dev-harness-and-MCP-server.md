---
id: TASK-023
title: Add and remove player items through the dev harness and MCP server
status: Done
assignee:
  - claude
created_date: '2026-10-28T20:30:00Z'
updated_date: '2026-10-28T21:37:00Z'
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
- [x] #1 Through the MCP server and run.py, an agent can read the player's current amount of a named game item
- [x] #2 Through the MCP server and run.py, an agent can set the player's amount of a named item to an exact number, where 0 removes it
- [x] #3 The result reports the item's amount before and after the change
- [x] #4 An unknown item name, or a negative or unreasonably large amount, is rejected with a clear error and changes nothing and does not crash the game
- [x] #5 After `invulnerable` then `vulnerable`, the player holds exactly the Mirror and Feathers amounts they had before `invulnerable`, verified in game
- [x] #6 Command parsing is covered by C# tests and the run.py and MCP command building by Python tests, written before the implementation
- [x] #7 The new command and MCP tool are verified in game through the MCP server, including setting an amount to 0 on a held item
- [x] #8 docs/development.md documents the command, the run.py subcommand and the MCP tool, and its description of `invulnerable` and `vulnerable` matches the behaviour
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
1. Root cause of the broken `vulnerable`: `ItemInventory.RemoveItem(EItem, bool)` drops one stack per call (log showed 19 and 1 after the restore), so it never reaches the original amount. Fix by setting the amount exactly, through the same helper the new command uses.
2. New harness command `item`: `{"command":"item","name":"Mirror"}` reads, `{"command":"item","name":"Mirror","amount":N}` sets (0 removes). Result: `{"item":name,"before":n,"after":n}`. Parser (C#, testable) validates `name` is a non-empty string and `amount` is an integer in 0..MaxItemAmount (999). Unknown names are rejected in the mod against the `EItem` members (Enum.TryParse, defined-only, so numeric strings are refused) before any change; errors flow through the existing failure result.
3. Mod: new `PlayerItems` static (GetAmount/SetAmount via AddItem delta up, repeated RemoveItem(.., false) down); `PlayerInvulnerability` restores originals through it. Dispatch in dev_harness.cs.
4. Python: `run.build_item_command(name, amount=None)`, `run.py item NAME [AMOUNT]`, MCP tool `item(name, amount?)`.
5. TDD order: C# parse tests and Python tests first, see them fail, then implement.
6. Verify in game via the MCP server: relaunch, read Mirror, set 3, set 0, bad name, negative, 100000; invulnerable then vulnerable restores exact amounts (also with a pre-held Mirror amount).
7. Update docs/development.md (command table, wire format, run.py, MCP tool, invulnerable/vulnerable description) and run `task check`.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified in game with the rebuilt DLL: run.py item and the MCP item tool read, set and zero Mirror; Nope, mirror, -1 and 100000 rejected with errors and no crash. Mirror 5 -> invulnerable 25 -> vulnerable -> reading before=5; fresh relaunch vulnerable gave Mirror 0 and Feathers 0 (previously 19 and 1). task check passes (1134 C# tests, 427 Python tests, lint). Commit 938bafc.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added an `item` harness command (`{"command":"item","name":N[,"amount":A]}`), `run.py item NAME [AMOUNT]` and MCP tool `item(name, amount?)` that read or exactly set the player's amount of an EItem and return `{item, before, after}`; 0 removes the item. Parsing rejects a missing or empty name and amounts outside 0..999; unknown or wrongly cased names are rejected in the mod before any change. `vulnerable` was leaving 19 Mirrors and 1 Feather because `ItemInventory.RemoveItem` drops one stack per call; it now sets both items back to the amounts held before `invulnerable` through the shared `PlayerItems.SetAmount`. Tests were written first (C# parse tests, Python command-building tests) and failed before the implementation. Verified in game through run.py and the MCP server, including setting a held Mirror to 0 and the invulnerable/vulnerable round trip. docs/development.md has a new Player items section and a corrected invulnerable/vulnerable description. Risk: items given through `item` while invulnerable are not tracked, so `vulnerable` restores only the Mirror and Feathers amounts from when `invulnerable` was sent (documented).
<!-- SECTION:FINAL_SUMMARY:END -->
