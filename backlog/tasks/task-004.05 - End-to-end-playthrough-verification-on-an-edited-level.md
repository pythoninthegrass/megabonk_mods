---
id: TASK-004.05
title: End-to-end playthrough verification on an edited level
status: To Do
assignee: []
created_date: '2026-10-06 21:42'
labels:
  - level-editor
dependencies:
  - TASK-004.02
  - TASK-004.03
  - TASK-004.04
parent_task_id: TASK-004
priority: medium
type: chore
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-004 first for full context. Depends on TASK-004.02 (edit application), TASK-004.03 (navmesh rebuild), and TASK-004.04 (upload guard) all being complete.

Hand-write (or script) a non-trivial `.mblevel.json` test level file exercising at least: one tile height change, one tile slope change, one added tile, one removed tile, one placed object (chest or decorative prop), and one removed generator-spawned object. Load it in the game and play a complete run from spawn to the boss portal, confirming:

- All edits are visually present and correct.
- Enemies path correctly throughout, including across edited terrain.
- No leaderboard/achievement/stats calls fire (check the log).
- No errors or crashes occur across the full run.

This is the integration acceptance gate for the entire TASK-004 parent — write up the test level file and the verification steps/results in docs/ so it can be re-run as a regression check after future changes (e.g. a game update, or TASK-005's editor UI changes).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A test .mblevel.json file exercises all six edit op types in one level
- [ ] #2 A full playthrough from spawn to boss portal on this level completes with all edits visually confirmed correct
- [ ] #3 Enemies path correctly across edited terrain throughout the full run
- [ ] #4 Log inspection confirms zero leaderboard/achievement/stats calls during the run
- [ ] #5 The test level file and verification steps are documented in docs/ as a reusable regression check
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
