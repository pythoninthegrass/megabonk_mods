---
id: TASK-022
title: 'Dev harness: toggle enemy spawns off and on'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-28 00:29'
updated_date: '2026-10-28 00:44'
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
- [x] #1 A harness command turns enemy spawning off and on, and a relaunch or level load restores the default
- [x] #2 `state` reports whether spawns are off
- [x] #3 With spawns off, no new enemies appear over a 60 second run, checked by the enemy count in the dev readout or the KillFloor heartbeat
- [x] #4 The command is available as a `run.py` subcommand and as an MCP tool in scripts/mcp_server.py
- [x] #5 Whether enemies already alive are cleared is decided and documented in docs/development.md, with the harness limits
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first: harness_command_tests.cs (parse `spawns` enabled true/false), harness_result_tests.cs (`spawns_off` in state JSON), tests/test_run.py (build_command) and the mcp_payloads state.json fixture. Run to confirm failing.
2. Add enemy_spawns.cs (pattern of PlayerInvulnerability): set EnemyManager.Instance.enabledWaves=false, remember original, report Off only for the same manager instance so level load/new run restores the default. If enabledWaves does not stop spawns in the running game, fall back to a Harmony prefix on EnemyManager.CanSpawnEnemy/SpawnEnemy gated by the switch.
3. Wire HarnessCommandKind + parser, dev_harness.cs handler, ReadState/GameStateSnapshot `spawns_off`, run.py `spawns on|off` subcommand, MCP tool `spawns(on)`.
4. Verify in game: relaunch, spawns off, compare enemy count (numEnemies / KillFloor heartbeat) at 0s and 60s, with spawns on as control.
5. Decision (approved): block new spawns only, do not clear enemies already alive. Document choice and limits (bosses/forced spawns if they bypass, reset on load) in docs/development.md.
6. Check ACs, final summary, single conventional commit (tests + implementation together, no attribution).
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a `spawns` harness command (`{"command":"spawns","enabled":bool}`), `run.py spawns on|off` and MCP tool `spawns(on)`. The mod sets `EnemyManager.enabledWaves`; `state` reports `spawnsOff`. Block-only: enemies already alive are not cleared. Verified on the example forest level: enemies 2-5 with spawns on, 0 for 67s after spawns off, 4 back within 2s of spawns on. Reset on level load is by a new EnemyManager; confirmed via relaunch only. Boss/shrine/summoner spawns not confirmed to respect enabledWaves (documented in docs/development.md "Enemy spawns").
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
