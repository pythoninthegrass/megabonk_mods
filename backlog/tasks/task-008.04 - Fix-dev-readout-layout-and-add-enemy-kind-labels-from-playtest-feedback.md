---
id: TASK-008.04
title: Fix dev readout layout and add enemy-kind labels from playtest feedback
status: Done
assignee:
  - pythoninthegrass
created_date: '2026-10-08 16:30'
updated_date: '2026-11-09 05:26'
labels:
  - level-editor
dependencies:
  - TASK-008.03
parent_task_id: TASK-008
priority: medium
ordinal: 46000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A playtest of the dev position readout (TASK-008.02/.03) surfaced usability problems: the on-screen cell/grid text clutters the screen and is better suited to a log; the label is right-aligned so lines shift horizontally as numbers change width, making it hard to read at a glance; every non-stage-boss actor is labelled "enemy" even when it is a miniboss (e.g. the stone golem) or an elite, which were indistinguishable from ordinary enemies; and the player's own line carries no label to distinguish it from actor lines.

This task fixes all four: move cell/grid/height text to a harness-gated debug log (keeping world position on screen), left-align the on-screen readout in fixed columns so lines never shift horizontally regardless of value width, give bosses/minibosses/elites their own distinct labels (with the boss-tier lines also showing the enemy type name), and add a "me:" label to the player's line.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 On-screen readout lines no longer show the grid cell, height level or "outside" text; the player's line is labelled "me:" to distinguish it from boss/enemy lines
- [x] #2 On-screen lines are left-aligned in fixed columns anchored under the minimap's bottom-left corner and grow to the right as values get longer; the start of each line and the position column do not shift horizontally as values change
- [x] #3 Enemies are classified into distinct labels (at minimum: final boss, stage boss, miniboss, elite, ordinary enemy) using the game's own enemy-flag data, with the classification rule documented including which flag the stone golem and other minibosses carry
- [x] #4 Boss-tier lines (final boss, stage boss, miniboss) additionally show the enemy's type name (e.g. MinibossGolem)
- [x] #5 The readout always lists all boss-tier actors, then a bounded number of elites, then a bounded number of ordinary enemies chosen by the existing nearest/below-floor rule, and stays readable with hundreds of enemies alive
- [x] #6 A harness-gated toggle logs the grid cell, height level and world position for the player and for boss-tier actors whenever the value changes, mirroring the existing kill-floor heartbeat toggle pattern (off by default, settable by both an environment variable and a harness command)
- [x] #7 The enemy-kind classifier, the line-formatting logic, the cell-change-log tracking, and the new harness command parsing all have unit tests written before the implementation
- [x] #8 Verified in the running game with a screenshot showing the new fixed-column layout with a "me:" line and at least one non-ordinary-enemy label
- [x] #9 docs/development.md documents the new on-screen format, the label/classification rule, and the cell-log toggle
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Full plan reviewed and approved by the maintainer; stored at /Users/<user>/.claude/plans/read-backlog-task-008-clever-waterfall.md during planning. Summary:

0. This task created.
1. Confirm the miniboss EEnemyFlag (expect Boss=2) by disassembling SummonerController.EventMiniboss (Binary Ninja via RVA from .tools/il2cpp_dump/dump.cs) and by runtime cell-log evidence.
2. New ActorKind classifier (actor_kind.cs) mapping EEnemyFlag bits -> {final boss, stage boss, miniboss, elite, enemy}, precedence FinalBoss(32) > StageBoss(4) > Miniboss(Boss2|SummonerMiniboss16) > Elite(1) > Enemy. Unit tests first.
3. Rework PositionReadout (position_readout.cs) to fixed-column left-aligned lines without cell/h/outside on screen: label, id, pos(x,y,z) each padded, trailing BELOW FLOOR / floor column, boss-tier lines append the EEnemy type name after a fixed-width gap. Player line labelled "me:". Keep CellOf/LevelOf; add FormatCellLog for the log path. Tests first (position_readout_tests.cs), including exact padded strings.
4. position_label.cs: anchor label bottom-left of minimap (anchorMin/Max (0,0), pivot (0,1)), TopLeft alignment, mspace rich text for fixed-width columns on the proportional cloned font. Verify widest line does not clip off the right edge of the screen.
5. Selection: boss-tier always listed (dedup via stageBosses + enemyFlag check), new elite selector capacity 3 (NearbyEnemySelector reused), ordinary enemy selector capacity 5 excluding boss-tier/elite.
6. Cell-change log: new pure CellChangeTracker (reserved id for player) + harness command "cells" (harness_command.cs, dev_harness.cs) + env var MEGABONK_CELL_LOG + scripts/run.py cells on|off, mirroring the existing heartbeat toggle. Tests first in all three layers.
7. docs/development.md updated: new screen format, kinds/flags (incl. confirmed golem flag), selection caps, cell-log toggle and command table entry.

Verification: task check (build+xunit+ruff+pytest); in-game screenshots at two player positions showing stable columns and "me:"; miniboss triggered via a temporary uncommitted probe calling the game's own EventMiniboss; run.py cells on/off checked against Latest.log. Conventional commits, no attribution, per CLAUDE.md.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Step 1 (miniboss flag): static disassembly skipped — Binary Ninja is GUI-only here (no headless Python API installed, and a full analysis pass on the 54MB GameAssembly.dll is too slow for this). Found the real game dir via `uv run scripts/game_paths.py` (CrossOver bottle on this Mac) and confirmed `EventMiniboss` RVA 0x487240 in .tools/il2cpp_dump/dump.cs for reference. Deferring confirmation to the runtime verification step: the new cell-log toggle will print the raw EEnemyFlag int on any boss-tier actor's first sighting, and the in-game probe that calls the game's own SummonerController.EventMiniboss will show the real flag the game assigns. Proceeding with code built on the documented EEnemyFlag bit values (Boss=2 expected for a miniboss) and will correct the classifier/docs if runtime evidence disagrees.

Steps 2-7 implemented and unit-tested (actor_kind.cs, position_readout.cs reworked, cell_change_tracker.cs, harness_command.cs + dev_harness.cs 'cells' command, scripts/run.py cells, position_label.cs reworked for bottom-left anchor/kinds/cell-log, docs/development.md updated). `task check` passes (310 C# tests, 35 python self-tests, markdownlint, ruff). Now verifying in the running game on the Mac's CrossOver install (deployed DLL hash confirmed matching the build). Relaunching Megabonk via `task game:run` is slow/flaky this session (steam:// URI not reliably starting the process); working through it before taking the AC8 screenshot and the miniboss probe.

Live verification this session (direct `cxstart` launches, documented as a new docs/development.md subsection "Launching from an automated session"):
- AC1/AC2/AC8: screenshots (mine and the maintainer's, including a real stage boss 'Lil Bark' fight) confirmed no cell/h/outside on screen, `me:` label present, columns left-aligned and stable, box no longer drifts to screen-center.
- AC3/AC4: stone golem/miniboss Boss-bit finding carries over from TASK-008.03's probe evidence (a miniboss spawned via SummonerController showed IsBoss()==true); this task's classifier (actor_kind.cs) reorganizes that same fact behind Enemy's public Is*() methods, not the private field. the maintainer's live screenshot showed a real stage boss line with its type name ('Ent1') appended after a single space (no reserved padding, per his 'shrink the last column' feedback).
- AC5: boss tier always listed; elites and ordinary enemies capped at 3 each per the maintainer's final request (down from 5).
- AC6: verified live this session - `run.py cells on` then loading a level produced `PositionLabel: me cell (10,7) h0 pos (120, 2, 3)` in Latest.log.
- AC7: 312 C# tests (up from 296 baseline) + 35 python self-tests, all written before their implementation.
- AC9: docs/development.md rewritten for the dynamic-column design, labels-with-colon, kinds table, cell-log section, plus a new 'Launching from an automated session' subsection documenting the cxstart workaround and the Monitor/yield wait pattern for future agents.

Design iterated live with the maintainer across several relaunch-and-screenshot rounds: fixed-width guessed columns -> dynamic per-refresh column widths (computed from actual displayed data, not hardcoded) using PadLeft/PadRight (C# interpolated-string alignment must be a compile-time constant, unlike Python f-strings, so it couldn't do runtime-width alignment) -> RobotoMono monospace font (enumerated via Resources.FindObjectsOfTypeAll<TMP_FontAsset>()) -> removed the reserved flag-column padding before boss-tier type names (was creating large dead space whenever only one row had a type name) -> id column floored to 3 digits so it doesn't jitter within a session -> anchor moved from the minimap's bottom-right (old right-aligned design) to also bottom-right but with left-aligned text inside a box sized every refresh via GetPreferredValues (bottom-left was tried first per an initial ask but clipped off-screen, since the minimap sits flush with the screen's own top-right corner) -> RightOffsetX tuned live (345 -> 245 -> 45 -> -10 -> -5 -> 0, final) to compensate for the minimap's RectTransform bounds not matching its visible edge.

Per a mid-session instruction, added a repo-wide rule (AGENTS.md "Comments in code (all languages)", and memory feedback_cs_comment_style.md): no section-banner/multi-paragraph comments in any file in this repo; max 1-2 lines, rationale goes in docs/*.md. Applied retroactively to every file touched this task.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Reworked the dev position readout after playtest feedback (TASK-008.02/.03): moved the grid-cell/height/outside text off screen into a harness-gated cell-change log (`run.py cells on|off`, mirroring the kill-floor heartbeat), classified actors into final boss/stage boss/miniboss/elite/enemy labels (`actor_kind.cs`, driven by the game's own `EEnemyFlag` bits read through `Enemy`'s public `Is*()` methods), gave the player's line a `me:` label, and switched the on-screen block to dynamically-sized columns computed each refresh from the data actually shown (`PositionReadout.Render`) instead of a fixed worst-case guess, rendered in a monospace font (`RobotoMono`) anchored under the minimap.

Iterated live with the maintainer through several rounds of rebuild-relaunch-screenshot: the label anchor, its horizontal offset, column widths/separators, the id column's 3-digit floor, and dropping a reserved flag-column before boss-tier type names (which was leaving large dead space) were all tuned against the running game, not guessed once and left. Also added a repo-wide no-section-comments rule (AGENTS.md + memory) triggered mid-session, applied to every touched file, and documented a reliable non-interactive game-relaunch workflow (`cxstart` direct launch bypassing Steam's URI handler, plus polling `Latest.log` for `DevHarness: enabled` instead of sleeping) for future agents.

Tests: all new logic (classifier, line rendering, cell-change tracking, harness command parsing, run.py's `cells` subcommand) was written before its implementation; 312 C# tests and 35 Python self-tests pass, `task check` is green.

Verified in the running game, including a real stage-boss encounter ("Lil Bark") showing a correctly labelled, type-named boss line, and the cell-log toggle producing the expected log line. The stone golem/miniboss `Boss` EEnemyFlag bit carries over from TASK-008.03's prior probe evidence rather than a fresh disassembly in this session (Binary Ninja here has no headless API and a full analysis pass on the 54MB GameAssembly.dll was impractical for this).

Docs: docs/development.md's "Position readout" section rewritten for the new format/column rule, "Enemy kinds" and "Cell-change log" subsections added, and a new "Launching from an automated session" subsection for future agents.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
