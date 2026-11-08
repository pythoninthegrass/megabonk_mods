---
id: DRAFT-001
title: 'Console verbs for XP, level, gold, silver and healing'
status: Draft
assignee: []
created_date: '2026-11-08T07:55:00Z'
labels: []
dependencies:
  - TASK-054.02
references:
  - .tools/il2cpp_dump/dump.cs
  - src/MegabonkLevels.Mod/player_items.cs
parent_task_id: TASK-054
priority: low
type: feature
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Proposed while planning the console and not yet confirmed by the maintainer, so it stays a Draft until approved. Neither run.py nor the mod can change the player's XP, level, gold or silver, or heal the player. Testing late-run balance, shop and shrine flows, or low-health behaviour today means playing up to that state. These are the Fallout `player.setlevel` / `player.additem 0000000f` equivalents.

Proposed gated verbs (★, MEGABONK_DEV): `player.add_xp n`, `player.set_level n`, `player.add_gold n`, `player.add_silver n`, `player.heal [n]` (alias `player.reset_health` for full heal).

Leads from the Il2Cpp dump (`.tools/il2cpp_dump/dump.cs`, regenerate with `task re:dump`), unverified at runtime:
- `PlayerXp.AddXp(int)`.
- `PlayerInventory.ChangeGold(int)`, `PlayerInventory.AddXp(int)` and `PlayerInventory.AddSilver(int)`.
- `ProgressionSaveFile.AddSilver(int)`, which writes the persistent save and must **not** be used. Silver here should affect only the current run, unless the maintainer decides otherwise.
- `Enemy.Heal(int)` exists. The player-health equivalent still needs locating.

Each verb should also be a harness command with run.py/MCP wrappers, for parity with the rest of the console.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Maintainer approves scope (which verbs, and whether silver may touch the persistent save) before the task leaves Draft
- [ ] #2 Each approved verb changes the value in a live run, confirmed through harness state or a screenshot
- [ ] #3 Each verb is gated behind MEGABONK_DEV and has a harness command with run.py/MCP wrappers and tests for its payload and console binding
- [ ] #4 Leaderboard/achievement/stats guards for custom levels still hold after using the verbs
- [ ] #5 docs/development.md documents the verbs and the game methods they call
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
