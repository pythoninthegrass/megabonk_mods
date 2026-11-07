---
id: TASK-048.01
title: Curate a self-contained starter level for public downloads
status: In Progress
assignee: []
created_date: '2026-11-07 01:56'
updated_date: '2026-11-07T22:37:00Z'
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

Redesigned the starter after reviewing Super Mario 64 Bob-omb Battlefield footage as a level-design reference: renamed Mosswatch Hollow to Bramblecrown Hill (slug bramblecrown-hill) and rebuilt it on the 15x15 maximum grid with heights -1 to 4, twelve ramps, a central hill whose only route up is an eighteen-step spiral to a summit boss arena, a fence-line leading line from spawn, and seven districts (meadow, gully, ridge, ruins, pen, highland, spiral) with a chest each and shrine locations in five or more. Selection art redrawn around the hill. Tests written first (15x15 grid, height set, full reachability, summit climb of at least 15 steps, per-district chests and shrine spread); 60 focused Python/package tests and the C# starter test pass, task lint passes.

Runtime check on the authoring Mac under plain Wine via the development harness: 225 tiles, 383 fill pieces and 149 edits built, boss spawner on the summit, kill floor armed, no missing-content, failed-edit or exception log lines; spawn, summit, peak and gully views captured to the gitignored evidence folder. Not repeated for this layout: native-input ramp walking, a combat interval with spawns on, the boss interaction, the first-edit save and replay, and the packaged selection screen. No commit made yet.

Follow-up from play feedback: Greed and Magnet shrines spawned by the extra-shrine pass lay sideways (the mod assumed Y-up models for every kind but Moai; Greed, Magnet, Challenge, Cursed and Balance are Z-up) and chests were authored at X=0 instead of the native 270. Fixed in ExtraShrines.LocalUp and a per-prop NATIVE_ROTATION_X registry in the level builder, with tests; verified live (shrines at 0/270 as the game's own, chests at 270 with the game's small tilt).

Added level-file fields shrineKindRanges (per-run random count per kind, with ShadyGuy now a spawnable kind) and groundZones (per-cell-range ground material), a read-only palette harness command (run.py palette, MCP palette) that dumps every catalog id with its prefab name, and a 2 second editor tooltip dwell. Bramblecrown Hill is now a composite of Forest, Graveyard, Dungeon, Desert and Hell districts with biome ground, 5 guaranteed Charge shrines and 3-8 Moai and Shady Guy per run. Live-checked a spawned Shady Guy opening its shop. Not yet verified: native-input ramp walking, combat, boss, Moai and coffin interactions, first-edit replay, packaged selection screen. Lava and mixed bosses still need mod code.

Later in the same redesign: the lava pool is a sunken basin with a ramp out and a refused spawn inside any lava zone; Forest grass blades are dropped on repainted ground; boss and miniboss pool draws are burned for the rest of the run so an enemy never spawns twice. Committed as 55fe187. The task stays open: still to verify on this layout are native-input ramp walking, a full combat run, the Moai and coffin interactions, the first-edit save and replay, the packaged selection screen, and a green task check (blocked by the installer parity and THPS fixture failures present at HEAD).
<!-- SECTION:NOTES:END -->
