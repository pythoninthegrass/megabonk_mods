---
id: TASK-067.08
title: >-
  Make the Squeaker save guard cover every character-keyed save and verify it
  with the mod removed
status: To Do
assignee: []
created_date: '2026-11-13T05:17:00Z'
labels:
  - character
  - bepinex
dependencies: []
references:
  - src/MegabonkLevels.Mod/squeaker_save_guard_patch.cs
  - src/MegabonkLevels.Mod/squeaker_registration_patch.cs
documentation:
  - docs/characters.md
parent_task_id: TASK-067
priority: medium
type: task
ordinal: 234000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Squeaker must never leave data in the player's saves that the stock game cannot load once the mod is removed. The current guard keeps id 21 out of config.json and out of the character progression table, and config.json was checked after a Squeaker session. It was never verified with the mod removed, progression.json is encrypted so its contents could not be inspected from outside, and other saves keyed by character were not examined (for example the per-tier set of completed characters and the statistics saves). Squeaker's registration and the guard are described in docs/characters.md under "Squeaker in the game" and "Not verified". The goal is evidence, not just more code: either every Squeaker-written save is shown to be free of the id, or the gaps are closed until it is.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every save structure a Squeaker session can write that is keyed or valued by a character is identified from the game's code and listed in docs/characters.md
- [ ] #2 After a Squeaker session, none of those saves contains the Squeaker id in what is written to disk, shown by inspecting the decoded content (the progression save is encrypted)
- [ ] #3 Any structure found to carry the id is kept clean by the guard, and the guard still leaves the in-memory values unchanged for the running session
- [ ] #4 On a copy of the save directory taken after a Squeaker session, the stock game with the mod removed starts and loads, with unlocks, progression and the selected character intact
- [ ] #5 The guard's decision logic that can be separated from the game is covered by unit tests written before the code
- [ ] #6 docs/characters.md states what was verified and how, and its Not verified section no longer lists the items this task closes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
