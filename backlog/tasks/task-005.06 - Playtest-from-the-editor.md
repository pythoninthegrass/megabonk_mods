---
id: TASK-005.06
title: Playtest from the editor
status: To Do
assignee: []
created_date: '2026-10-06 21:43'
labels:
  - level-editor
dependencies:
  - TASK-005.05
parent_task_id: TASK-005
priority: medium
type: feature
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005 first for full context.

Implement a "playtest" action in the editor UI that takes the current (possibly unsaved) edit state, reloads the stage with it applied (reusing TASK-004's load/apply/navmesh-rebuild pipeline directly against the in-memory edit list rather than requiring a save-to-disk round-trip first), restores normal gameplay (un-pauses, re-enables player control/damage, restores the normal camera), and lets the player walk/fight through it like a real run. Provide a clear way to return to the editor afterward (e.g. re-pressing the editor keybind) without losing the edit history that was being playtested.

Verify the leaderboard/achievement/stats guard from TASK-004.04 also applies during a playtest session, since a playtest run should never be treated as a legitimate scored run either.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A playtest action applies the current in-memory edit state (not requiring a prior save) and restores normal gameplay so the player can walk/fight through it
- [ ] #2 Returning to the editor after a playtest preserves the edit history that was being tested
- [ ] #3 The leaderboard/achievement/stats guard from TASK-004.04 is confirmed active during playtest sessions
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
