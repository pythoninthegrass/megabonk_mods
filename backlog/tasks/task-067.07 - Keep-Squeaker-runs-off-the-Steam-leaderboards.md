---
id: TASK-067.07
title: Keep Squeaker runs off the Steam leaderboards
status: To Do
assignee: []
created_date: '2026-11-13T05:17:00Z'
labels:
  - character
  - bepinex
dependencies: []
references:
  - src/MegabonkLevels.Mod/steam_write_guard_patch.cs
  - src/MegabonkLevels.Mod/custom_level_state.cs
  - src/MegabonkLevels.Mod/squeaker_registration_patch.cs
documentation:
  - docs/characters.md
  - docs/level-format.md
parent_task_id: TASK-067
priority: high
type: feature
ordinal: 233000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Squeaker is a mod-added character (id 21, past the stock enum). A run as Squeaker on a stock level currently uploads a normal leaderboard score carrying that id, which players without the mod cannot decode, and the game keeps a server-side banned_players leaderboard, so a modded run must never reach Steam as if it were stock. The mod already suppresses leaderboard, achievement and stat writes for custom-level runs, but that guard is keyed only on whether a custom level is active, so a Squeaker run on a stock level is not covered. Squeaker's own registration is described in docs/characters.md; the existing custom-level guard is described in docs/level-format.md and was built under TASK-004.04 (read it first). Open question for the worker: whether achievement unlocks and Steam stat writes from a Squeaker run should be suppressed too, or only leaderboard uploads; record the decision and its reasoning in docs/characters.md.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A leaderboard upload attempted during a run as Squeaker is skipped and logged, on a stock level and on a custom level
- [ ] #2 A run as Calcium or any other stock character on a stock level still uploads its leaderboard score exactly as before
- [ ] #3 The existing custom-level suppression of leaderboard, achievement and stat writes behaves as before
- [ ] #4 The decision on achievement and stat writes for Squeaker runs is made, implemented accordingly and recorded in docs/characters.md
- [ ] #5 The rule that decides whether a run is excluded is pure logic with unit tests written before the code, covering Squeaker, stock characters, custom levels and their combinations
- [ ] #6 docs/characters.md no longer lists the leaderboard gate as unfound and describes the exclusion
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
