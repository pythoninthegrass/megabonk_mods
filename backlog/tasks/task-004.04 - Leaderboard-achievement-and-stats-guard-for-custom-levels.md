---
id: TASK-004.04
title: 'Leaderboard, achievement, and stats guard for custom levels'
status: To Do
assignee: []
created_date: '2026-10-06 21:42'
labels:
  - level-editor
dependencies:
  - TASK-004.01
parent_task_id: TASK-004
priority: high
type: feature
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-004 first for full context.

While a custom/edited level (loaded via TASK-004.01) is active, Harmony-prefix (or otherwise intercept) `SteamLeaderboardsManagerNew`'s `QueueLeaderboardUpload` and `UploadLeaderboardScore` so they are skipped entirely — the game maintains a server-side `banned_players` leaderboard, and players running custom levels must never risk getting flagged as cheaters for scores that didn't come from legitimate procedural generation. Also skip Steam achievement and stats writes during a custom-level run (identify the exact classes/methods — likely `SteamAchievementsManager`/`SteamStatsManager` per earlier research, confirm exact method names against the real dump/game).

This guard must be scoped precisely: it should NOT affect normal, non-modded runs at all — only suppress these calls when a level loaded via this mod's level-file mechanism is active. Verify both states: a normal run still uploads/writes normally (don't break the base game's own functionality), and a custom-level run suppresses all of them.

Log every suppressed call at an appropriate log level so this is auditable/verifiable, not a silent behavior that's hard to confirm is actually working.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 QueueLeaderboardUpload and UploadLeaderboardScore are skipped during any run started from a custom level file loaded via TASK-004.01, verified by log inspection
- [ ] #2 Steam achievement and stats writes are identified by exact class/method name (confirmed against the real game, not assumed) and skipped during a custom-level run
- [ ] #3 A normal, non-modded run still performs leaderboard uploads, achievement unlocks, and stats writes exactly as before this mod was installed
- [ ] #4 Every suppressed call during a custom-level run is logged for auditability
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
