---
id: TASK-044
title: Harness command and MCP tool to kill enemies and bosses
status: To Do
assignee: []
created_date: '2026-11-05 19:46'
updated_date: '2026-11-05 19:46'
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
- [ ] #1 The task records whether the harness kill goes through the game's real damage and death handlers, and which path it uses
- [ ] #2 A harness command and MCP tool can kill the nearest enemy, all enemies and all bosses, with unit tests for the argument handling and reply shape
- [ ] #3 Killing a boss with the tool raises the same boss events a real kill does, verified in the running game
- [ ] #4 docs/development.md lists the new command and tool
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
