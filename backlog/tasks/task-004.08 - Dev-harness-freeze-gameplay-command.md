---
id: TASK-004.08
title: 'Dev harness: freeze gameplay command'
status: Done
assignee:
  - Claude
created_date: '2026-10-08 03:41'
updated_date: '2026-10-08 03:51'
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
- [x] #1 A harness command freezes gameplay through the game's own time/pause logic, and a matching command resumes it, with each logged
- [x] #2 While frozen, enemies, spawners and the run timer stop and the player cannot die, with no pause menu in the screenshot
- [x] #3 The harness keeps polling and screenshots still render while frozen, verified in the running game
- [x] #4 `run.py freeze` and `run.py resume` subcommands exist, and `cycle` accepts a flag that freezes before the screenshot
- [x] #5 Pure command parsing for the new commands is unit tested, with the tests written before the implementation
- [x] #6 The commands and any pause caveats (dialogs, whether `A_Pause` fires) are documented in docs/development.md
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first: C# harness_command_tests for freeze/resume parsing; scripts/test_run.py for build_command and cycle --freeze arg parsing. Confirm they fail.
2. Add Freeze/Resume to HarnessCommandKind and HarnessCommand.TryParse.
3. DevHarness.Execute: Freeze calls MyTime.Pause(), Resume calls MyTime.Unpause(), each logged. No Harmony patch.
4. run.py: freeze and resume subcommands; cycle --freeze freezes before the screenshot.
5. Verify in the running game under CrossOver: A_Pause behaviour, enemies/spawners/run timer stop, harness still polls and renders while frozen.
6. Document commands and caveats in docs/development.md; run task check; conventional commit without attribution.
Decision: harness-local, independent of TASK-005.01 (YAGNI); sharing is left to 005.01.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
MyTime.Pause()/Unpause() set MyTime.paused (logged True/False). Verified under CrossOver: HUD run timer, enemy and player identical across two screenshots 4s apart, harness polled and rendered while frozen, no pause window.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added freeze/resume harness commands that call MyTime.Pause/Unpause, run.py freeze/resume subcommands, and cycle --freeze. Parsing is unit tested (tests written first). Documented in docs/development.md. Kept harness-local; sharing with TASK-005.01 is left to that task.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
