---
id: TASK-032.06
title: Port the THPS Warehouse to a from-scratch level
status: Done
assignee: []
created_date: '2026-11-04 20:37'
updated_date: '2026-11-05 19:42'
labels: []
dependencies:
  - TASK-032.03
  - TASK-032.04
parent_task_id: TASK-032
priority: high
ordinal: 159000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Parent TASK-032. The shipped Warehouse (levels/thps.mblevel.json) and the piece-assembled variant (levels/thps-editable.mblevel.json) get their blank slate by deleting the stock Forest piece by piece: 224 tile.remove and 966 object.remove out of 1241 edits. The builders hardcode per-seed object counts, keep a hidden spawn cell at (10,7), and keep the generated PlayerSpawnPortal and BossSpawner.

Regenerate both levels as from-scratch files from scripts/build_thps_level.py and scripts/build_thps_editable_level.py: emit the authored grid (only the floor actually needed, or none if the mesh carries everything), spawn, bossSpawner and the existing placements, and drop the tile and clutter removals, the seed object counts, the kept object categories and the hidden spawn cell. Keep gameplay identical: rails, shrines, chests, boombox, music and the boss redirect. Check whether the generated ForestParticles that the old level kept needs an explicit placement.

The preservation baseline (tests/fixtures/thps-preservation.json, scripts/check_thps_preservation.py) pins the old output byte for byte; regenerate it deliberately and explain why in the commit body. Write the builder tests first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Both regenerated Warehouse levels are from-scratch files containing no gen: targets and no tile edit ops, and carrying spawn and bossSpawner
- [x] #2 Builder tests written first assert those properties for both builders
- [x] #3 The preservation baseline is regenerated and the reason is in the commit body
- [x] #4 The shipped Warehouse loads, starts at the spawn without a reset or Forest flash, and plays through to the boss and portal, verified in the running game
- [x] #5 The piece-assembled variant loads and its placements match the pre-port set
- [x] #6 Load time on the Warehouse is not slower than before, with before and after timings recorded in the task
- [x] #7 docs/thps-warehouse-layout.md no longer describes the hidden spawn cell or the removal counts
- [x] #8 From-scratch files can carry an optional bossRedirect flag, kept through load and save, and the boss spawn redirect arms on a from-scratch level that sets it, so the Warehouse boss summons outside the glass box
- [x] #9 The bossSpawner entry can carry an optional scale and hiddenChildren, applied when the spawner is instantiated, so the Warehouse portal keeps its 0.4 scale and hidden BottomPiece and Collider
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Redirect (C#, TDD): add an optional boolean bossRedirect to LevelFile (from-scratch only, omitted when false), keep it through FromScratchSnapshot/FoldFromScratch; ShouldArm arms on a from-scratch level only when it is set; update level-format and development docs. The redirect itself picks a ring spot around the spawner and reads no destination, so no position field is added.
2. Builder tests first (tests/test_build_thps_level.py, test_build_thps_editable_level.py): replace tile/clutter/GENERATED_SPAWN_CELL tests; assert baseline none, schema 4, grid, spawn, bossSpawner, bossRedirect true, no tile.* ops, no gen: targets, unchanged placement set.
3. Builders: drop tile_edits, clutter_removals, SEED_*, KEPT_OBJECT_CATEGORIES, GENERATED_SPAWN_CELL, spawn_moves; emit minimal grid, spawn from PLAYER_START, bossSpawner at the portal position (170,15.6,27 yaw 90); keep authored killFloorY.
4. Check in game: empty/single-cell grid loads (else keep one hidden cell under spawn); ForestParticles need an explicit placement; hidden BottomPiece/Collider children on the from-scratch bossSpawner.
5. Regenerate tests/fixtures/thps-preservation.json and fix check_thps_preservation.py (kept_cells); reason in commit body.
6. Docs: remove hidden spawn cell and removal counts from docs/thps-warehouse-layout.md, thps-warehouse-pieces.md, development.md.
7. Verify in running game: load time before/after, no reset or Forest flash, play to boss and portal, editable variant placements match; task check; conventional commit, no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Before timing (shipped Warehouse, 1241 edits, run 1 via relaunch): StartNewMap 22:20:47.355 -> A_GenerationComplete +2.03s -> LiveEdit applied +3.35s -> KillFloor armed +3.40s -> StartupCover player placed +7.27s.

Decision (Lance): from-scratch files carry the redirect destination in a new optional bossRedirect field, kept verbatim through load and save. bossSpawnPosition keeps its editor-marker meaning on from-scratch sessions. AC #8 reads bossRedirect where it says bossSpawnPosition.

Correction (Lance approved): BossSpawnRedirect never reads a destination (TryFindSpot rings around the spawner), so the bossRedirect position field is replaced by an optional boolean bossRedirect opt-in flag.

Decision (Lance): extend the from-scratch bossSpawner entry with optional scale and hiddenChildren (applied by FromScratchGenerationPatch after it instantiates the spawner) so the Warehouse portal keeps object.move's 0.4 scale and hidden BottomPiece/Collider. Done C# step 1 part 1: LevelFile.BossRedirect plus ShouldArm opt-in, 1944 C# tests green.

After timing (from-scratch Warehouse, 48 edits, 15x15 grid with one hidden floor tile, run 1): StartNewMap 11:32:21.133 -> A_GenerationComplete +1.90s -> LiveEdit applied +2.01s -> KillFloor armed +2.02s -> StartupCover player placed +5.95s. Before was +2.03 / +3.35 / +3.40 / +7.27s. No reset or Forest flash in the log: one 'player placed' line, no timeout warning.

Finding: an empty grid does not work. With zero tiles the game's catch floor derives as int.MaxValue, the kill floor armed at 2.1e9 and the player died on spawn. The grid therefore keeps one hidden floor tile at the old cell (10,7) on the 15x15 stock-size grid (so its world position is unchanged), at level -2 instead of -1 so the catch floor is -60 and the authored kill floor of -35 applies exactly (at -1 the game raised it to -32).

Pre-port placements: object.place edits are byte-identical before and after for both levels (48 shipped, 251 editable); only the tile ops, gen: removals and boss move were dropped.

Verified in the running game (shipped Warehouse): loads with 48 edits, one 'player placed' line at (109, 36.08, -116), no timeout warning, KillFloor armed at -35 (catch floor -60), ForestParticles(Clone) present without a placement. Boss: interacting with the spawner armed the redirect, which moved the boss from (180.7, 27.5, 24.2) to (171.6, 15.7, 68.7), outside the box (z 20.9-31.4). Editable variant loads with 251 edits, same placement and kill floor lines.

NOT verified (AC #4 left unchecked): defeating the boss and reaching the portal. The harness has no tool that kills an enemy, so the run was not played through past the boss summon. Commit 8b58001.

AC #4 confirmed by Lance on a second machine (shipped Warehouse at 08a1847): played to the boss portal, summoned two bosses with a Boss Curse active, and beat them. The redirect moved them to (171.3, 12.4, -8.7) and (145.9, 12.4, 88.1), outside the box. A tier 1 run has no second stage, so the run continues into endless waves after the kill; there is no stage-exit portal to check.

Open observation, not diagnosed: at 13:34:07, about 42 s after the summon, six Enemy1 fell through to the kill floor within 0.25 s around the main half pipe (x 136-166, z -25 to 38). No pre-port log exists to compare against.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Ported both Warehouse levels (levels/thps.mblevel.json, levels/thps-editable.mblevel.json) to from-scratch files. The builders no longer emit tile ops, gen: removals, seed counts or the boss object.move; they emit a grid, spawn, bossSpawner and bossRedirect, with object.place edits identical to the pre-port set (48 shipped, 251 editable). The grid keeps one hidden floor tile at (10, 7), level -2, because an empty grid makes the game derive its catch floor as int.MaxValue and kill the player on spawn; level -2 keeps the authored kill floor of -35 exact. Mod changes: optional bossSpawner scale and hiddenChildren, optional bossRedirect flag that keeps the boss redirect on for a from-scratch level, shared ChildHider. Load reached 'player placed' at +5.95 s against +7.27 s before. The preservation baseline is regenerated on purpose, and the unused boss_spawn_position helper and its tests are removed. Verified in the running game on two machines: load, spawn, kill floor, redirect moving both bosses out of the box, and beating the bosses. Commits 8b58001 and 08a1847.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
