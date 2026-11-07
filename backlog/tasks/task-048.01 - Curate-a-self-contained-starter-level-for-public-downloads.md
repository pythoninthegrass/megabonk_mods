---
id: TASK-048.01
title: Curate a self-contained starter level for public downloads
status: In Progress
assignee: []
created_date: '2026-11-07 01:56'
updated_date: '2026-11-07 02:54'
labels:
  - onboarding
dependencies:
  - TASK-047
documentation:
  - docs/player-guide.md
  - docs/player-installer.md
  - docs/starter-level.md
parent_task_id: TASK-048
priority: high
type: enhancement
ordinal: 177000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Give the default player package a small polished level suitable for first play and a first edit. Existing level files include development regression maps; do not indiscriminately bundle them. The starter must work using the owned game's runtime resources and approved distributable project content, without THPS packs or soundtrack files.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The default public player package includes one clearly titled, playable starter level with an appropriate publicly distributable selection image.
- [x] #2 First play works with no optional packs or custom music installed and produces no missing-content placeholders.
- [x] #3 The level supports a simple edit-save-replay tutorial and excludes scratch/regression maps from the default experience.
- [x] #4 A packaged runtime smoke test and starter-content documentation establish the expected first-play result.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Inspect current packaging/tests and Fedora runtime; survey Forest, Desert and Graveyard and resolve native Forest prefabs.
2. Write failing tests for the authored starter grid, ordinary-mobility reachability, pack/music independence, reproducibility and default package selection.
3. Add a reproducible Mosswatch Hollow builder, 11x11 three-elevation native Forest level, original distributable selection artwork and explicit default package content.
4. Document the expected first-play experience and a move-rock/save-copy/replay tutorial.
5. Build and install the default Linux package on Fedora; verify the selection entry/art, clean pack-free first play, collision/routes/enemies/boss and actual editor save/replay, preserving existing optional content.
6. Run focused/full checks, review changes, record evidence and finalize only verified criteria.

Runtime inspection found that from-scratch generation omits cliff/fill geometry. Add tested exposed-edge planning and invoke the existing native fill applier before collision baking, then rebuild the package and retest on Fedora. No schema change or game-asset redistribution is needed.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Maintainer approved the Mosswatch Hollow woodland starter design and explicitly requested runtime testing on Fedora. Proceeding with this scoped content task despite the parent documentation dependency still being open; public publication remains separate.

Test-first baseline: seven starter/content tests failed before implementation, then 56 focused Python/package tests passed (one platform skip); shipped level also parses and validates all 121 cells with the C# validator. Initial packaged Fedora installation and --check succeeded on game build 21750826; normal player menus display the starter title, thumbnail, biome icon and Tier 1-only selection. Optional Levels/LevelPacks/CustomMusic are preserved outside UserData during isolated tests.

Fedora native-input ramp checks with Calcium and zero Feathers reached the western ridge at body Y≈21.925, the watchpost plateau at Y≈41.925, and the northern terrace at Y≈21.925 without jumping. Normal CanInteract checks opened the free chest and summoned the stage boss; the harness subsequently killed that boss through the damage path. These are smoke checks, not an unassisted full survival clear.

Final authored content has 121 cells, 10 ramps and 102 native object placements. Corrected vegetation rotations to match live native prefab X=270° rather than laying imported trees/logs/bushes sideways, with a regression test. Final packaged first play on Fedora ran 27 game seconds with normal damage, spawns on, zero Feathers and Calcium; HUD showed 21 kills, level 1, 101/101 HP, and profiler counted up to eight live enemies. The final first-edit saved 103 edits as my-mosswatch-final; packaged original remained byte-identical, and the rock moved from X=12 to X≈23.867 at Z=-148.

Checks: 2012 C# tests pass; 57 focused Python/package tests pass (one platform skip); lint passes. task check is blocked by unchanged installer parity output ('Installed' vs 'installed') and three existing THPS generated/preservation fixture failures. Rebuilding the native Go installer did not resolve parity. Python suite excluding the parity file and those three specific cases passes; no unrelated product changes made.

Fresh-process replay verified the saved rock's live Transform at (23.87, 0, -148), with no missing-content, failed-edit, ERROR or exception lines. All three native maps were surveyed live on Fedora. Restored the original Levels/LevelPacks/CustomMusic, retained the final starter, stopped game and injected menu devices, and reran the final installer --check successfully. Evidence is in gitignored .tools/evidence/mosswatch/; package is .tools/megabonk-levels-dev-ml0.7.3-linux.zip.

Confirmed the validation blockers predate these changes: extracted clean HEAD to an isolated temporary baseline, shared only local generated inputs, and reproduced the installer install-fresh parity failure plus all three THPS fixture failures unchanged (four failures). C# suite: 2012 passed. Python excluding the parity file and those three named cases: 1281 passed, three skipped. All acceptance criteria are verified, but the task remains In Progress because task check is not green; no commit has been made.

Committed the starter implementation with a conventional commit at the maintainer's request. The task remains In Progress only because the full check is blocked by independently reproduced baseline failures. Fleet synchronization excludes the deferred host.
<!-- SECTION:NOTES:END -->
