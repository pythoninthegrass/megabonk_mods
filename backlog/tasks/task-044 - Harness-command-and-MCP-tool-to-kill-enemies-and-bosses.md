---
id: TASK-044
title: Harness command and MCP tool to kill enemies and bosses
status: Done
assignee: []
created_date: '2026-11-05 19:46'
updated_date: '2026-11-05T20:25:00Z'
labels:
  - harness
  - mcp
dependencies:
  - TASK-043
references:
  - >-
    backlog/tasks/task-032.06 -
    Port-the-THPS-Warehouse-to-a-from-scratch-level.md
  - scripts/mcp_server.py
modified_files:
  - docs/development.md
  - scripts/mcp_server.py
  - scripts/run.py
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/harness_command.cs
  - src/MegabonkLevels.Mod/enemy_kill_targets.cs
  - src/MegabonkLevels.Mod/enemy_killer.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - tests/MegabonkLevels.Tests/harness_command_tests.cs
  - tests/test_damage_mcp.py
  - tests/test_run.py
priority: medium
ordinal: 164000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The MCP server can kill or damage the player (kill, damage) and stop spawns, but nothing hurts an enemy. TASK-032.06 AC #4 (play the Warehouse through the boss kill) could not be verified by the agent for that reason and needed the maintainer to play it.

First read how the game kills an enemy (the damage and death path, and what the A_BossDied, A_BossDefeated and A_StageBossDied events depend on in dump.cs) and decide whether a harness kill goes through the real damage handlers. A kill that skips them could pass a check a real kill would fail, so prefer calling the game's own damage or die method over destroying the object. Then add a harness command in the mod and an MCP tool in scripts/mcp_server.py, for example one that kills the nearest enemy, all enemies, or all bosses, with the same reply shape as damage. Depends on the boss event logging task so the result can be read from the log.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The task records whether the harness kill goes through the game's real damage and death handlers, and which path it uses
- [x] #2 A harness command and MCP tool can kill the nearest enemy, all enemies and all bosses, with unit tests for the argument handling and reply shape
- [x] #3 Killing a boss with the tool raises the same boss events a real kill does, verified in the running game
- [x] #4 docs/development.md lists the new command and tool
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
1. Research (done): Enemy has public DamageExternal(DamageContainer) -> private Damage, plus Enemy.Kill(string) and DiedNextFrame. EnemyManager.enemies (Dictionary<uint,Enemy>) lists live enemies; Enemy.IsBoss/IsStageBoss/IsFinalBoss classify. A_StageBossDied is a static Action on EnemyManager; method bodies are native-only, so the death path is confirmed empirically rather than by decompile.
2. Path decision: submit lethal damage through Enemy.DamageExternal with a DamageContainer (damage >= hp, BypassAll|IgnoreArmor|BossDamage flags) so the game's own Damage and death handlers run; fall back to Enemy.Kill only if DamageExternal cannot kill a boss (invulnerable phases). Confirm in the running game that A_EnemyDied, then A_StageBossDied, fire.
3. TDD: C# tests in harness_command_tests.cs for parsing `kill-enemies` with `target` nearest|all|bosses (reject missing/unknown); Python tests for run.build_kill_enemies_command and the MCP `kill_enemies` tool (payload, invalid target rejected before sending, mod rejection surfaced).
4. Implement: HarnessCommandKind.KillEnemies + parser, EnemyKiller in the mod (reply: target, requested/killed counts, bosses killed, ids), dev_harness dispatch; run.py builder, subcommand and dispatch; mcp_server.py tool.
5. Verify in the running game on the Warehouse: kill the boss, read A_StageBossDied / A_BossDefeated from the log; also nearest and all.
6. Docs: command and tool in docs/development.md. Run task check.
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a kill-enemies harness command (targets nearest, all, bosses), run.py kill-enemies and MCP kill_enemies. Path: lethal DamageContainer (1,000,000 damage, BypassAll|IgnoreArmor|BossDamage, source HarnessKill) submitted through Enemy.DamageExternal, i.e. the game's own damage and death handlers, not Enemy.Kill or destroy. Verified live on the Warehouse: killing the spawned stage boss logged A_StageBossDied, A_BossDefeated False and A_NumBossesDefeated 1. Unit tests cover the C# parser and the Python builder/MCP tool; task check passes. The MCP tool itself was not called live (the running MCP server predates it); the same command was driven through run.py. Frozen-editor kills untested.
<!-- SECTION:FINAL_SUMMARY:END -->
