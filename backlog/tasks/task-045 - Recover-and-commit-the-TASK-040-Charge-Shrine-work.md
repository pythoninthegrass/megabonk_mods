---
id: TASK-045
title: Recover and commit the TASK-040 Charge Shrine work
status: To Do
assignee: []
created_date: '2026-11-05 20:08'
labels:
  - thps
  - recovery
dependencies: []
references:
  - >-
    backlog/tasks/task-040 -
    Place-3-5-Charge-Shrines-in-the-Warehouse-clear-of-grind-lines-and-ollie-landings.md
  - >-
    backlog/tasks/task-032.06 -
    Port-the-THPS-Warehouse-to-a-from-scratch-level.md
  - src/MegabonkLevels.Mod/extra_shrines.cs
  - src/MegabonkLevels.Mod/extra_shrines_patch.cs
priority: high
ordinal: 165000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-040 is marked Done and was verified in the running game, but its implementation never reached main. Commit 0bdb894 added only maximin.cs, the chest-luck files, tests and the task record. No commit touches shrineSpots, extraShrinesMax, guaranteedShrineKinds or chestLuckRange in code (git log --all -S finds only 0bdb894, and only in the task prose). At a2748f1, before TASK-032.06, levels/thps.mblevel.json and scripts/build_thps_level.py had none of those fields, and level_file.cs has no ExtraShrinesMax, ShrineSpots, GuaranteedShrineKinds or ChestLuckRange. Rebuilding the mod from main therefore lost the Warehouse's Charge Shrines, which the maintainer noticed.

This is not a regression from TASK-032.06. The old Warehouse removed all 15 generated ChargeShrine objects and placed none back.

The source is probably uncommitted on wm2 (offline when this was filed); an earlier uncommitted draft is also recorded at ~/megabonk_mods-wip-20261101.tgz there. mbp, mini, mf and fedora were checked: clean trees, no stash, and deployed DLLs with none of the shrine strings, so nothing is recoverable from them.

Recover the work from wm2 (git status, git stash list, the wip archive), commit and push it, then merge it with the from-scratch Warehouse builder from TASK-032.06: build_thps_level.py and the level JSON were rewritten there, and the new level keys are additive on a from-scratch file. TASK-040 described: extraShrines and extraShrinesMax (2 to 3 Charge Shrines per run), eight authored shrineSpots, 10% golden chance, guaranteedShrineKinds (one each of Magnet, Challenge, Boss Curse and Moai), chestLuckRange (-0.5 to 2), distance-weighted spot draws through Maximin, and the authored placement path in extra_shrines.cs and extra_shrines_patch.cs. If wm2 holds nothing usable, reimplement from the TASK-040 final summary.

Open question: SpawnShrines is skipped on a from-scratch level, but extra shrines are a separate pass. Confirm in the running game that it still runs on the from-scratch Warehouse.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The TASK-040 source (extra_shrines authored path, level_file.cs fields, builder changes, level JSON) is committed and pushed to main, recovered from wm2 or reimplemented from the TASK-040 summary with the choice recorded in the task
- [ ] #2 The level fields extraShrinesMax, shrineSpots, guaranteedShrineKinds and chestLuckRange load, round trip and are covered by tests
- [ ] #3 The from-scratch Warehouse builders emit the shrine and chest-luck settings, and the preservation baseline is regenerated with the reason in the commit body
- [ ] #4 Verified in the running game on the from-scratch Warehouse: 2 to 3 Charge Shrines per run and per restart at the authored spots, and the guaranteed Magnet, Challenge, Boss Curse and Moai shrines
- [ ] #5 docs/level-format.md and docs/thps-warehouse-layout.md describe the fields and the authored spots
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
