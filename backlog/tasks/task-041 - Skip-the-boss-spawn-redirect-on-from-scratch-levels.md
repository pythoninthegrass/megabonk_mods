---
id: TASK-041
title: Skip the boss spawn redirect on from-scratch levels
status: Done
assignee: []
created_date: '2026-11-04 23:42'
updated_date: '2026-11-04 23:44'
labels: []
dependencies:
  - TASK-032.04
priority: medium
ordinal: 161000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Parent TASK-032. BossSpawnRedirectPatch arms for every mod-loaded level (CustomLevelState.IsActive). It exists to move bosses out of the Warehouse's suspended glass box so they are not trapped in the rafters; a from-scratch level places its own boss spawner and has no such box. On from-scratch-fixture.mblevel.json the redirect logged a move from (84.5, 11.9, -0.6) to (138.5, 11.9, -1.1), yet the boss readout later showed the boss at (81, 25, 0), back at the spawner cell, so something else repositions it afterwards. Skip arming the redirect when the level is from-scratch, then check in game where the boss settles when the authored spawner is used.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 BossSpawnRedirect.ShouldArm is false for a from-scratch level and unchanged for other mod-loaded levels, covered by a test written first
- [x] #2 Triggering the authored boss spawner on a from-scratch level logs no BossSpawnRedirect move
- [x] #3 The in-game position the boss settles at on the fixture level is recorded in the task notes
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Test first: ShouldArm(customLevelActive, fromScratch) is false when fromScratch, true for an active non-from-scratch custom level, false when no custom level is active.
2. Change BossSpawnRedirect.ShouldArm and pass FromScratchGenerationPatch.ActiveLevel != null from the Interact prefix.
3. Relaunch the fixture level, trigger the spawner, confirm no BossSpawnRedirect log, record where the boss settles.
4. Update docs/development.md boss redirect section, task check, conventional commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
In game on from-scratch-fixture.mblevel.json with the redirect skipped: triggering the spawner logged no BossSpawnRedirect line. The boss stayed in cell (5,3), the spawner's cell, with its pivot between y=12 and y=38 over about 30 seconds (cell log shows h1/h2 changes), i.e. it hops around the spawner rather than being sent away. The earlier run with the redirect armed logged a move to (138.5, 11.9, -1.1) but the readout later showed the boss back at the spawner; why was not determined.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
BossSpawnRedirect.ShouldArm now takes a fromScratch flag and is false for from-scratch levels; the Interact prefix passes FromScratchGenerationPatch.ActiveLevel != null. Test written first (ShouldArm_NeverOnAFromScratchLevel). docs/development.md boss redirect section notes the exclusion. Verified in game that no redirect is logged and the boss stays at the authored spawner.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
