---
id: TASK-048.01
title: Curate a self-contained starter level for public downloads
status: In Progress
assignee: []
created_date: '2026-11-07 01:56'
updated_date: '2026-11-08T01:26:00Z'
labels:
  - onboarding
dependencies:
  - TASK-047
documentation:
  - docs/player-guide.md
  - docs/player-installer.md
  - docs/starter-level.md
  - docs/map-generation-determinism.md
  - docs/runtime-map-structure.md
  - docs/development.md
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
- [ ] #4 A packaged runtime smoke test and starter-content documentation establish the expected first-play result.
- [ ] #5 The generated starter preserves its authored grid, spiral/summit route and explicit prop transforms; regeneration is reproducible and the shipped JSON equals scripts/build_starter_level.py output.
- [ ] #6 Shrine counts use documented tighter bounds than the current 13–24 plan, with documented useful district guarantees that are verified on successfully placed shrines without blocking ramps or the spiral.
- [ ] #7 Shrine planning and replacement boss/miniboss picks use independent level-seeded streams reset per run; identical seeds and controlled event sequences reproduce plans/picks, including seed 0, without making ordinary combat or loot deterministic.
- [ ] #8 The summit boss and miniboss rosters are curated for introductory difficulty and arena suitability; repeat avoidance, shared pool state, curse copies and exhausted-pool fallback have explicit, tested behavior.
- [ ] #9 Starter descriptions/documentation identify the five biomes as visual districts over Forest gameplay, explain what the seed does and does not pin, and do not imply biome materials change stock enemy rosters.
- [ ] #10 The final regenerated layout passes offline plain-Wine repeated-seed checks and packaged first-play/edit-save-replay smoke checks, including ordinary-mobility routes, combat, boss, lava escape and Moai/merchant/coffin interactions; evidence and limitations are recorded.
- [ ] #11 Fresh load, the player-facing death Confirm/Restart path and saved-copy replay reset custom RNG/used-name state and restore authored content/start correctly; effective stage-0 spacing is verified as 40 horizontally and 20 vertically.
- [ ] #12 Final-layout checks demonstrate physical enemy/boss traversal without a navmesh rebuild or assumed Warehouse redirect, normal unforced interaction access and zero-added-Feathers mobility; documentation states that Tier 1 continues survival after the boss without a next-stage portal.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
- [ ] #5 Final-layout evidence records the generated level/build identity, offline plain-Wine runtime, repeated-seed comparisons and actual placement outcomes; earlier Mosswatch/layout smoke checks are not reused as final validation.
- [ ] #6 All final validation claims distinguish static/code findings, measured runtime behavior and unconfirmed assumptions; scope remains curated content and its randomization hooks, not a district encounter engine.
- [ ] #7 Validation uses current Go installer checks and records effective runtime stage parameters, inventory/control settings and per-instance custom-content comparisons; stock generation hashes alone do not certify custom placement reproducibility.
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Current plan: tighten Bramblecrown Hill's authored five-biome layout and gameplay randomization. This supersedes the original Mosswatch Hollow implementation plan; retain prior implementation notes as historical evidence, not validation of the final layout.

1. Preserve scripts/build_starter_level.py as the source of levels/bramblecrown-hill.mblevel.json. Keep baseline:none, the authored grid, spiral/summit route and explicit prop transforms; the builder's random.Random(481) already makes decoration reproducible. Do not replace this with stock maze or procedural-mesh generation.
2. Establish the randomization contract before implementation: authored terrain/props remain fixed; shrine planning and replacement boss/miniboss selection use independent, phase-distinct level-seeded streams reset per run; ordinary combat, loot and other stock gameplay remain random. Seed 0 is a valid forced level seed, not an opt-out. Read docs/map-generation-determinism.md and the actual mod hooks rather than assuming debugSeed covers every RNG.
3. Write failing tests for same-seed repeatability (including seed 0), stream independence, reset on a new run, shrine budget bounds and district coverage, and boss-pool exhaustion. Cover the pure planning logic before changing runtime patches.
4. Tighten shrine budgets in the generator (currently 5 Charge + 3–8 Moai + 3–8 Shady Guy + 2–3 extras, or 13–24 planned shrines). Select and document narrower count ranges and useful guaranteed district coverage. Replace both GUID-seeded RNGs in extra_shrines_patch.cs with phase-distinct seeded planning streams. Ensure guarantees concern successfully placed shrines; report placement failures and validate fallback/nudging does not obstruct ramps or the spiral.
5. Curate a smaller boss/miniboss roster appropriate to the summit arena and introductory difficulty, retaining cross-biome variety only where playable. Replace boss_pool_patch.cs's process-lifetime unseeded Random with a per-run seeded selection stream. Explicitly define and test shared used-name behavior and exhausted-pool fallback, including curse copies and repeated miniboss events; a singleton pool must not be presented as pinning every spawn under current exhaustion semantics.
6. Keep the five biomes as visual districts over the Forest map configuration. Update starter descriptions to explain that foreign ground materials and props do not change stock enemy rosters or generation rules; district-specific encounter systems are outside this task unless separately approved. Preserve ordinary combat/loot randomness and document the limits of seed reproducibility.
7. Regenerate the level from the builder, verify generated-file equality and the canonical bramblecrown-hill slug across tests, packaging and docs, then update docs/starter-level.md with the chosen shrine budgets, district guarantees, boss roster, seed contract and first-edit expectations.
8. Validate using the offline plain-Wine installation with the Steam stub, not CrossOver or a logged-in Steam session. Coordinate exclusive runtime ownership before launch/relaunch. Across at least two fresh-process runs with the same level seed, compare shrine plans/counts/kinds/districts and replacement boss/miniboss selection under the same controlled spawn sequence. Distinguish repeatable planning from physics-dependent placement; record any unconfirmed behavior explicitly.
9. Repeat final-layout native-input ramp/spiral walking with ordinary mobility, a combat interval with spawns on, summit boss and lava/escape checks, Moai/merchant/coffin interactions, first-edit save/fresh-process replay, and packaged selection/pack-free loading. Record evidence against the final generated file and deployed build, without claiming a full survival clear from a smoke test.
10. Run focused Python/C# tests, markdown lint and task check; reassess historical blockers rather than assuming they still exist. Review only task-owned changes, make conventional attribution-free commits, and check ACs/DoD only against fresh objective evidence.

Refinements after reading the measured stage investigation in TASK-053 and the runtime/load-path documentation:
11. Reset shrine/boss selection streams and used-name state at the generation lifecycle boundary, not only PrepareRun/StartNewMap. Death-screen Retry bypasses both. Test fresh-process load, the actual death Confirm → summary Restart buttons, and saved-copy replay; direct restart-run is a diagnostic, not button-path evidence.
12. Keep stageIndex:0 and tier:0. Read effective currentStage/currentMapParameters with query-objects at bounded depth and verify the authored coordinate contract (scaledTileWidth 40, scaledTileHeight 20). Requested stage overrides did not reliably select the measured generator assets; the cause is unconfirmed. Do not expand this task into fixing tier/stage selection or generalizing authored coordinates to other stage metrics.
13. Compare explicit custom shrine plans and placed instances, replacement boss/miniboss sequences and authored transforms, not global generation hashes: stock Forest objectsHash remains bimodal under reseeding, and Desert's empty object snapshot proves no prop determinism. Seeded planning does not promise physics-identical combat or placement without measurement.
14. Preserve the existing initial exposed-edge fill pass and collision rebuilding. Validate enemy/boss traversal of the spiral, cliffs and dense props physically; open maps have no navmesh to rebuild. Leave bossRedirect off for this authored arena unless a measured failure justifies opting in; the Warehouse ring is not a generic summit fix.
15. Document and check the post-boss Tier 1 outcome: no next-stage portal, continued survival. Do not promise a portal-based finish or add multi-stage support.
16. Ordinary-mobility checks must explicitly verify zero added Feathers and no harness invulnerability grant; relaunch defaults to two Feathers and invulnerable also adds them. Use Calcium or another character without Tony's fall-damage immunity. Validate normal CanInteract access without force; teleports/forced interaction are diagnostics, not proof of walkability/accessibility. Keep normal combat/loot randomness.
17. Use the current Go installer checks. The Python installer/parity tests were removed; historical parity failures are not current blockers without reproduction. Run task check afresh and record only present failures.
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

Maintainer requested that the determinism recommendations become the current implementation plan and unchecked ACs/DoD. Planning update only: no gameplay implementation or new runtime validation performed. Reopened the existing runtime/documentation AC and completion-hygiene items for the changed final scope; retained historical notes and earlier completed packaging criteria. Correctness constraints: level seed 0 already enables forced seeding; shrine and boss replacement RNGs are independent mod-owned randomness; EnemyManager.SpawnBoss at 0x41A200 does call positional SpawnEnemy at 0x41A3F0, so the earlier claim that it spawns nothing must not guide implementation. Offline plain Wine with the Steam stub is the requested validation runtime.
<!-- SECTION:NOTES:END -->
