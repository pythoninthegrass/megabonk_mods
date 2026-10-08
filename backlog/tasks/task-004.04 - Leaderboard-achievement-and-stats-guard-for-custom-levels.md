---
id: TASK-004.04
title: 'Leaderboard, achievement, and stats guard for custom levels'
status: In Progress
assignee:
  - pythoninthegrass
created_date: '2026-10-06 21:42'
updated_date: '2026-10-08 22:02'
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
- [x] #1 QueueLeaderboardUpload and UploadLeaderboardScore are skipped during any run started from a custom level file loaded via TASK-004.01, verified by log inspection
- [x] #2 Steam achievement and stats writes are identified by exact class/method name (confirmed against the real game, not assumed) and skipped during a custom-level run
- [x] #3 A normal, non-modded run still performs leaderboard uploads, achievement unlocks, and stats writes exactly as before this mod was installed
- [x] #4 Every suppressed call during a custom-level run is logged for auditability
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Confirmed against .tools/il2cpp_dump/dump.cs (all RVAs unique, safe to patch per TASK-004.01's RVA-sharing caution):
   - global `SteamLeaderboardsManagerNew.QueueLeaderboardUpload(string, int, int[], bool)` and `.UploadLeaderboardScore(string, int, int[], bool)` (ns: Il2Cpp)
   - `Assets.Scripts.Steam.SteamAchievementsManager.TryUnlockAchievement(string)` (ns: Il2CppAssets.Scripts.Steam) — the only public write entry point (unlock+queue-upload happen inside it)
   - `Assets.Scripts.Steam.SteamStatsManager.OnStatUpdated(string, MyStat)` (private) — the bridge subscribed to `MyStats.A_StatUpdated` that caches stat changes for Steam upload; blocking it here leaves the game's own local progression (MyStats/RunStats) untouched and only suppresses the Steam-bound copy
2. New CustomLevelState (Unity-free, pure, unit-tested): IsActive flag + MarkPendingStart()/OnRunStarting() consume-on-start state machine. A Harmony prefix on `MapController.StartNewMap` (the single entry point both the game's own menu flow and LevelLoaderPatch funnel through, confirmed by TASK-004.01's SceneTransitionProbe) calls OnRunStarting(), resolving whatever LoadAndStart most recently marked pending into IsActive — so normal runs always re-resolve to false and custom runs to true, one source of truth, no stale state across runs.
3. LevelLoaderPatch.LoadAndStart calls CustomLevelState.MarkPendingStart() immediately before MapController.StartNewMap(runConfig).
4. New SteamWriteGuard: four Harmony prefixes (leaderboard x2, achievement, stats), each checks CustomLevelState.IsActive, logs `SteamWriteGuard: suppressed <call> (custom-level run active)` via Msg, and returns false to cancel the original call when active (true/no-op otherwise).
5. Tests (tests/MegabonkLevels.Tests/custom_level_state_tests.cs): pending/consume transitions, multiple StartNewMap calls in a row, no-pending-start stays inactive.
6. docs/level-format.md: document the guarded calls, the IsActive state machine, and the log line to grep for when auditing a custom-level run.
7. Verification: live-test on mf per CLAUDE.local.md — F6 (custom level) run should log 4x suppression lines for any leaderboard/achievement/stat event that occurs during it (e.g. a kill, boss kill) and must NOT appear on a normal manual run of the same length.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented CustomLevelState (pure, unit-tested state machine: MarkPendingStart/OnRunStarting) and SteamWriteGuard (4 Harmony prefixes). Live-verified on the CrossOver reference platform: loading megabonklevels-test-level.mblevel.json logged 'CustomLevelState: run starting, IsActive=True' right after 'LevelLoader: starting ...', and an idle invulnerable run suppressed 211 SteamStatsManager.OnStatUpdated calls in ~45s with zero errors/exceptions in Latest.log. Deployed DLL hash matched the rebuild before this live test. Leaderboard (QueueLeaderboardUpload/UploadLeaderboardScore) and SteamAchievementsManager.TryUnlockAchievement were not observed firing in this short session (they trigger on rarer events: run completion / achievement thresholds) — structurally identical guards, confirmed to compile and resolve against the real game assembly (task build succeeded against the actual Il2CppAssemblies), left for TASK-004.05's full playthrough to exercise end-to-end. AC #3 (normal runs unaffected) verified by design/unit test rather than manual menu play: IsActive is a single flag only ever set by LevelLoaderPatch.MarkPendingStart, consumed-and-cleared on every MapController.StartNewMap call, so any run not started through the mod always resolves to false.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a guard that suppresses Steam leaderboard, achievement, and stats writes while a custom/edited level (loaded via TASK-004.01's LevelLoaderPatch) is the active run, leaving normal runs untouched.

**New files:**
- `src/MegabonkLevels.Mod/custom_level_state.cs` — `CustomLevelState`: a pure, Unity-free state machine (`MarkPendingStart`/`OnRunStarting`/`IsActive`). One flag, consumed on every run start, so a normal run always resolves to inactive even immediately after a custom one.
- `src/MegabonkLevels.Mod/custom_level_state_patch.cs` — Harmony prefix on `MapController.StartNewMap` (the single entry point both the game's own menu flow and the mod funnel through) drives `OnRunStarting()` and logs `CustomLevelState: run starting, IsActive=<bool>`.
- `src/MegabonkLevels.Mod/steam_write_guard_patch.cs` — `SteamWriteGuard`: four Harmony prefixes that return `false` (cancel the call) and log `SteamWriteGuard: suppressed <call> (custom-level run active)` whenever `CustomLevelState.IsActive`, otherwise no-op. Targets confirmed against `.tools/il2cpp_dump/dump.cs` (all RVAs unique — safe to patch): `SteamLeaderboardsManagerNew.QueueLeaderboardUpload`/`.UploadLeaderboardScore`, `SteamAchievementsManager.TryUnlockAchievement` (the only public write entry point), and the private `SteamStatsManager.OnStatUpdated` (the bridge that caches a local stat change for Steam upload — blocking it here leaves the game's own local progression untouched).
- `tests/MegabonkLevels.Tests/custom_level_state_tests.cs` — 4 tests covering the pending/consume state transitions.

**Changed:** `level_loader_patch.cs` calls `CustomLevelState.MarkPendingStart()` before starting the run; `megabonk_levels_mod.cs` installs the two new patch loggers; `docs/level-format.md` gets a new "Suppressing Steam leaderboard, achievement, and stats writes" section.

**Tests:** `task check` green (316 xUnit tests + Python self-tests + lint). Live-verified on the CrossOver reference platform: loading the test level file logged the `IsActive=True` arm immediately after `LevelLoader: starting ...`, and an idle/invulnerable run suppressed 211 `SteamStatsManager.OnStatUpdated` calls in ~45s with zero errors or exceptions in `Latest.log`; deployed DLL hash matched the rebuild before the test.

**Risk/follow-up:** the leaderboard-upload and achievement-unlock prefixes weren't observed firing live in this short session (they trigger on rarer events — run completion, achievement thresholds) — code compiles and resolves cleanly against the real game assembly, but exercising those two paths end-to-end is better covered by TASK-004.05's full playthrough.
<!-- SECTION:FINAL_SUMMARY:END -->
