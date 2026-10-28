---
id: TASK-022
title: 'Dev harness: toggle enemy spawns off and on'
status: To Do
assignee: []
created_date: '2026-10-28 00:29'
labels:
  - dev-harness
  - tooling
dependencies: []
references:
  - TASK-004.08
  - TASK-004.10
  - TASK-021.05
  - TASK-021.06
  - TASK-021.07
documentation:
  - docs/development.md
priority: medium
ordinal: 95000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
During playtests and automated checks (TASK-021.05 walkability runs, TASK-021.06 item placement, TASK-021.07 music) enemies keep spawning and harassing the player, and `invulnerable` is only the Mirror effect, not a god mode: stronger enemies and some damage sources still kill the player (docs/development.md). `freeze` stops enemies but also stops the player, so it cannot stand in for a playthrough.

Add a harness command that stops the game's enemy spawning and can turn it back on, following the pattern of `freeze` (TASK-004.08) and `invulnerable` (TASK-004.10): a pure command parser covered by unit tests, a harness handler, a `run.py` subcommand and an MCP tool, with the state reported in `state`. Find the spawn path in `.tools/il2cpp_dump/dump.cs` (`rg -u`; start with `EnemyManager`) and decide whether to block new spawns only or also clear the enemies already alive; record the choice and its limits in docs/development.md.

Out of scope: granting items or choosing level-up upgrades beyond the existing `dismiss-levelup` command.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A harness command turns enemy spawning off and on, and a relaunch or level load restores the default
- [ ] #2 `state` reports whether spawns are off
- [ ] #3 With spawns off, no new enemies appear over a 60 second run, checked by the enemy count in the dev readout or the KillFloor heartbeat
- [ ] #4 The command is available as a `run.py` subcommand and as an MCP tool in scripts/mcp_server.py
- [ ] #5 Whether enemies already alive are cleared is decided and documented in docs/development.md, with the harness limits
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
