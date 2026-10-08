---
id: TASK-004.08
title: 'Dev harness: freeze gameplay command'
status: To Do
assignee: []
created_date: '2026-10-08 03:41'
labels:
  - level-editor
dependencies:
  - TASK-004.06
parent_task_id: TASK-004
priority: medium
ordinal: 39000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Extend the dev harness (TASK-004.06; docs/development.md) with a freeze command so a screenshot can be taken without the idle player dying or the level-up dialog opening. First step: read the rest of the `MyTime` method list in .tools/il2cpp_dump/dump.cs to find the game's real pause entry point (MyTime has `paused`, `timeScale` and an `A_Pause(bool)` event that components subscribe to via their `OnPause(bool)` handlers), and confirm whether setting the `paused` field alone fires `A_Pause`. `PauseUi.Pause()` is the menu pause and would put the pause window in the frame, so prefer the `MyTime` path. Confirm in the running game that a frozen game still runs the harness poll and still renders, since MelonLoader's OnUpdate does not depend on the game's clock.

Freezing only suits screenshots: enemies stop too, so it cannot stand in for the playthrough in TASK-004.03 / TASK-004.05.

Related: TASK-005.01 needs to freeze gameplay for the in-game editor. Settle whether this harness freeze and that one share a single implementation before building either.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A harness command freezes gameplay through the game's own time/pause logic, and a matching command resumes it, with each logged
- [ ] #2 While frozen, enemies, spawners and the run timer stop and the player cannot die, with no pause menu in the screenshot
- [ ] #3 The harness keeps polling and screenshots still render while frozen, verified in the running game
- [ ] #4 `run.py freeze` and `run.py resume` subcommands exist, and `cycle` accepts a flag that freezes before the screenshot
- [ ] #5 Pure command parsing for the new commands is unit tested, with the tests written before the implementation
- [ ] #6 The commands and any pause caveats (dialogs, whether `A_Pause` fires) are documented in docs/development.md
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
