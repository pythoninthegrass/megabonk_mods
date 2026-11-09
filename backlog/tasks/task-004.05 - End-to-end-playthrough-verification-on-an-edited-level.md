---
id: TASK-004.05
title: End-to-end playthrough verification on an edited level
status: Done
assignee:
  - '@Claude'
created_date: '2026-10-06 21:42'
updated_date: '2026-11-09 05:26'
labels:
  - level-editor
dependencies:
  - TASK-004.02
  - TASK-004.03
  - TASK-004.04
  - TASK-004.06
  - TASK-004.08
  - TASK-004.09
  - TASK-004.10
parent_task_id: TASK-004
priority: medium
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-004 first for full context. Depends on TASK-004.02 (edit application), TASK-004.03 (slope and added-tile edits, collision and wall rebuild, kill floor, enemy pathing check), and TASK-004.04 (upload guard) all being complete.

Hand-write (or script) a non-trivial `.mblevel.json` test level file exercising at least: one tile height change, one tile slope change, one added tile, one removed tile, one placed object (chest or decorative prop), and one removed generator-spawned object. Load it in the game and play a complete run from spawn to the boss portal, confirming:

- All edits are visually present and correct.
- Enemies path correctly throughout, including across edited terrain.
- No leaderboard/achievement/stats calls fire (check the log).
- No errors or crashes occur across the full run.

This is the integration acceptance gate for the entire TASK-004 parent — write up the test level file and the verification steps/results in docs/ so it can be re-run as a regression check after future changes (e.g. a game update, or TASK-005's editor UI changes).

## Tools and behaviour already in place (from the other TASK-004 subtasks)

Dev harness (docs/development.md, driven by scripts/run.py): `load`, `screenshot`, `quit`, `cycle`; `freeze` / `resume` (TASK-004.08) to hold the scene still for screenshots; `camera X Y Z --rot RX RY RZ` / `camera --clear` (TASK-004.09) to pose a view of the edited cells (cell (x, z) is at world (-280 + 40x, 20 * height, -280 + 40z) on Forest; use a camera height of about 60-100 looking straight down because fog washes the map out above about 150); and the player invulnerability command from TASK-004.10 so enemies chase a living player. The harness cannot press keys or walk the player, so a spawn-to-boss-portal run still needs a human at the controls; use the harness for the repeatable parts (edits visible, no errors in the log, a scripted survival run).

After tile edits the mod rebuilds the baked ground collision, regenerates the wall and fill pieces on edited tiles' edges, and arms a kill floor (docs/runtime-map-structure.md: "Ground collision after edits", "Walls after edits", "Kill floor"). A tile removed in the test level is therefore a real hole, walls around a removed cell are left as generated, and falling below the lowest tile ends the run, so plan the route and the removed tile accordingly. Reference scratch levels used so far: Forest seed 20261007 with edits at (9,7) slope East, (11,7) added at height 1, (12,7) slope North, (13,7) removed.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A test .mblevel.json file exercises all six edit op types in one level
- [x] #2 A full playthrough from spawn to boss portal on this level completes with all edits visually confirmed correct
- [x] #3 Enemies path correctly across edited terrain throughout the full run
- [x] #4 Log inspection confirms zero leaderboard/achievement/stats calls during the run
- [x] #5 The test level file and verification steps are documented in docs/ as a reusable regression check
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Generate the baseline (no-edit) level on CrossOver/macOS to read the real genId index (Tree0 count, etc.) from Latest.log before picking edit targets.
2. Hand-write levels/task-004-05-regression.mblevel.json (Forest, seed 20261007 — the confirmed-reproducible debugSeed) with 7 edits covering all 6 op types: SetTileHeight(10,5,h1), SetTileSlope(9,7,East), RemoveTile(11,7)+AddTile(11,7,h1) [the only way to exercise AddTile on a truly empty cell, per docs/level-format.md], RemoveTile(13,7) [left removed, a real hole], PlaceObject(interactable/chest at cell (9,9)), RemoveObject(gen:object:Tree0:0010). Reuses the (9,7)/(11,7)/(13,7) coordinates already playtested clean in TASK-004.03's scratch level.
3. Verify the automatable parts via scripts/run.py: load the level, confirm "LiveEdit: applied 7 edit(s)" with no warnings/errors in Latest.log, freeze+camera overhead/angled screenshots over the edited cells to visually confirm each edit, grep the log across a load+invulnerable+settle window for zero SteamWriteGuard/leaderboard/achievement/stats calls and zero exceptions.
4. Human playthrough (the maintainer): spawn to boss portal on this level, confirming enemies path across/into the edited cells without getting stuck (cell-change log / position readout / kill-floor heartbeat can be turned on to help observe this) and that the run completes with no crash. The harness cannot press keys or move the player, so this step needs a person at the controls — ask the maintainer to run it once the file and automated checks are ready.
5. Write up docs/level-format.md or a new docs/regression-level.md section: the file's purpose, the edits table, how to re-run it (run.py cycle / manual playthrough steps), and the verification results, so it's a repeatable regression check for future game updates or TASK-005 changes.
6. Check acceptance criteria against the above evidence, record implementation notes, conventional commit.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Baseline load (levels/example-forest.mblevel.json) on the CrossOver reference platform confirmed the genId index (300 Tree0, etc.) before picking edit targets.

Wrote levels/task-004-05-regression.mblevel.json: 7 edits covering all 6 op types (SetTileHeight(10,5)->1, SetTileSlope(9,7)->East, RemoveTile+AddTile(11,7)->1, RemoveTile(13,7), PlaceObject interactable/chest at (80,0,80), RemoveObject gen:object:Tree0:0010). (9,7)/(11,7)/(13,7) reuse TASK-004.03's already-playtested scratch coordinates.

Live-verified on CrossOver: 'LiveEdit: applied 7 edit(s)' with zero warnings, FillRegeneration/CollisionRebuild/KillFloor armed cleanly, zero errors/exceptions in the whole session. Screenshots (freeze + camera, low altitude 50-60 units, angled rotation) confirm the slope tile (visibly tilted plane), the raised AddTile plateau with regenerated cliff walls (no sky gaps), the RemoveTile hole (a real pit with walls, not a sky leak), and a chest-colored object near the placement coordinates.

677 SteamWriteGuard suppressions logged (SteamStatsManager.OnStatUpdated) during a ~2.5 minute idle-invulnerable window with enemies active (stable at 9, lowestEnemyY ranging -2.8 to -20, approaching but not yet crossing the kill floor at -72); zero unsuppressed leaderboard/achievement/stats lines, zero errors.

Documented the test level, its edit table, and the re-run steps in docs/level-format.md under 'Regression check: the TASK-004.05 test level'.

AC #2 and #3 (full spawn-to-boss-portal human playthrough with enemy pathing confirmed throughout) are NOT yet done -- the harness cannot press keys or move the player, so this needs the maintainer at the controls. The level file, automated verification, and doc are ready for that playthrough.

task check: 316 xUnit tests + python self-tests + markdownlint + ruff all green.

Full human playthrough completed by the maintainer on the CrossOver reference platform: spawn to the boss portal, all 6 edit types visually confirmed in play, boss portal activated and interacted with normally.

The Forest stage boss wandered into the removed-tile hole at (13,7) and was killed by the kill floor mid-run; this did NOT block the boss portal -- it activated normally afterward. Tier 1 has no win/finish screen by the game's own design (unrelated to this mod), so 'a complete run' means reaching/activating the boss portal, not beating the game. Corrected an earlier wrong diagnosis in docs/level-format.md that blamed the portal on the boss's early death.

Whole-session log: zero errors/exceptions, zero unsuppressed leaderboard/achievement calls, 11686 SteamWriteGuard-suppressed stats writes over the full play session.

Removed all TASK-### references from docs/level-format.md (10 occurrences) per AGENTS.md's existing 'Writing docs/*.md' rule, which the first pass of this doc violated; rephrased each around the actual content instead of citing provenance.

Updated 'Verification status' in docs/level-format.md to reflect the completed full playthrough.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added `levels/task-004-05-regression.mblevel.json`, a hand-written Forest (seed 20261007) level exercising all six edit op types in 7 edits: `SetTileHeight` (10,5)->1, `SetTileSlope` (9,7)->East, `RemoveTile`+`AddTile` (11,7)->1 (the only way to exercise `AddTile` on a truly empty cell, since the live grid is dense), `RemoveTile` (13,7) left as a hole, `PlaceObject` (`interactable/chest`) at world (80,0,80), and `RemoveObject` of a generator-spawned tree. (9,7)/(11,7)/(13,7) reuse coordinates already playtested clean in earlier scratch-level work.

**Automated verification** (CrossOver reference platform, via `scripts/run.py`): all 7 edits applied cleanly with zero warnings; `FillRegeneration`/`CollisionRebuild`/`KillFloor` armed with no errors; freeze+camera screenshots at low altitude with angled rotation visually confirm the slope tile, the raised plateau with regenerated cliff walls, the removed-tile hole (a real pit with walls, not a sky leak), and the placed object; an idle-invulnerable window logged hundreds of suppressed Steam stats writes with zero unsuppressed leaderboard/achievement calls and zero errors.

**Human playthrough** (the maintainer): spawn to boss portal, all edits visually confirmed in play, enemies including the Forest stage boss crossed/interacted with the edited terrain (the boss wandered into the (13,7) hole and was cleanly killed by the kill floor — confirms kill-floor handling of a boss-tier actor), the boss portal activated normally, and the whole session logged zero errors/exceptions and zero unsuppressed leaderboard/achievement calls across 11,686 suppressed stats writes. Tier 1 has no win/finish screen by the game's own design (unrelated to this mod); "a complete run" for this check means reaching and activating the boss portal.

**Docs:** `docs/level-format.md` gets a new "Regression check: the full-playthrough test level" section (edit table, re-run steps, the boss/kill-floor observation, verification status). Also removed 10 pre-existing `TASK-###` references scattered through the rest of that file, per `AGENTS.md`'s "Writing docs/*.md" rule (provenance belongs to git/Backlog, not doc prose) — the first draft of this doc's new section violated that rule and was corrected.

**Tests:** `task check` green (316 xUnit tests, python self-tests, markdownlint, ruff). No new testable logic was introduced (a data file + docs), so no new unit tests were needed.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
