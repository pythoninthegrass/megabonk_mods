---
id: TASK-005.06
title: Playtest from the editor
status: Done
assignee:
  - lance
created_date: '2026-10-06 21:43'
updated_date: '2026-10-26T16:01:00Z'
labels:
  - level-editor
dependencies:
  - TASK-005.05
parent_task_id: TASK-005
priority: medium
type: feature
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005 first for full context.

Implement a "playtest" action in the editor UI that takes the current (possibly unsaved) edit state, reloads the stage with it applied (reusing TASK-004's load/apply/navmesh-rebuild pipeline directly against the in-memory edit list rather than requiring a save-to-disk round-trip first), restores normal gameplay (un-pauses, re-enables player control/damage, restores the normal camera), and lets the player walk/fight through it like a real run. Provide a clear way to return to the editor afterward (e.g. re-pressing the editor keybind) without losing the edit history that was being playtested.

Verify the leaderboard/achievement/stats guard from TASK-004.04 also applies during a playtest session, since a playtest run should never be treated as a legitimate scored run either.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A playtest action applies the current in-memory edit state (not requiring a prior save) and restores normal gameplay so the player can walk/fight through it
- [ ] #2 Returning to the editor after a playtest preserves the edit history that was being tested
- [ ] #3 The leaderboard/achievement/stats guard from TASK-004.04 is confirmed active during playtest sessions
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
## Goal
Add a Playtest action to the editor that replays the current in-memory edits as a fresh, playable run, and returns to the editor on F8 with the undo/redo history intact.

## Key facts from the codebase
- `EditorTileTools._session` is an `EditorEditSession` (undo/redo stack + save-state bookkeeping). It lives in `editor_tile_tools.cs` and is reset only in `OnEditorEntered` when `_sessionRunGeneration != RunGeneration`, and in `LoadSelected`.
- `EditorTileTools.OnEditorEntered` is called from `EditorMode.Enter`. During playtest the editor is off, so `EditorTileTools.Tick`/`OnEditorEntered` do NOT run, meaning `_session` is preserved across the reload — the only reset is on return.
- `LiveEditPatch` holds its own runtime `_session` (planner/applier/grid/objects), recreated in `OnGenerationComplete` each generation. `SeedEdits` returns its seeded edits. `SnapshotLevelFile(edits)` builds a `LevelFile` from the current map/stage/tier/seed + edits.
- `LevelLoaderPatch.LoadAndStart(path, logger)` deserializes from disk, forces the seed, calls `SetPendingEdits` + `CustomLevelState.MarkPendingStart`, then `MapController.StartNewMap`. This is the shared start path to reuse.
- `CustomLevelState.IsActive` is set true by the `StartNewMap` Harmony prefix when `_pendingStart` was marked, and `SteamWriteGuard` suppresses leaderboard/achievement/stats writes while `IsActive`. Reusing the same start path arms the guard automatically.
- `PlayerInvulnerability` is harness-driven (Mirror item). A new run builds a new inventory, so the player is vulnerable by default, but the old inventory's Mirror must be cleared.
- Open tile maps bake no navmesh; enemy movement is Rigidbody-based (see docs/runtime-map-structure.md), so tile edits need no navmesh rebuild.

## Design
1. `LevelLoaderPatch`:
   - Extract the validated start logic into `Start(LevelFile level, MelonLogger.Instance logger)` returning bool (true once `StartNewMap` is reached).
   - Keep `LoadAndStart(path, logger)` as a thin wrapper that deserializes and calls `Start`.
   - The bool lets the editor report failure without a save-to-disk round-trip.

2. `EditorTileTools`:
   - Add a `PlaytestState` holding the preserved `EditorEditSession` and `_lastSavedEditCount`.
   - Add `Playtest(logger)`: build the `LevelFile` via `SnapshotLevelFile(_session.CurrentEdits)`; capture `_playtest`; start via `LevelLoaderPatch.Start`; clear invulnerability; exit editor mode. On any failure, restore `_playtest`/editor state and report via toast.
   - Modify `OnEditorEntered`: when `_playtest != null`, restore the preserved session (`_session`, `_sessionRunGeneration = RunGeneration`, `_lastSavedEditCount`) instead of resetting; clear `_playtest`. Otherwise keep the existing generation-change reset.
   - Add a Playtest toolbar button (disabled while loading / no live session).

3. `EditorMode`:
   - No behavior change; F8 re-entry already works via `EditorReenterPolicy`. Returning triggers `OnEditorEntered`, which restores the session.

## Tests (Unity-free, written first)
- `editor_playtest_tests.cs`:
  - `SnapshotLevelFile` includes current edits, excludes undone edits, needs no save.
  - `Playtest` captures the session so undo/redo survive a reload; an unrelated run clears the retained session; duplicate clicks cannot start overlapping reloads; invalid snapshot/failed start leaves history intact and reports failure.
  - `OnEditorEntered` restores the preserved session when `_playtest` is set, and resets normally otherwise.
  - `CustomLevelState` guard: marking pending start arms `IsActive` (reuse existing `custom_level_state_tests` pattern).

## Verify in the running game (docs/development.md harness)
1. Make unsaved terrain + object edits; leave an op for redo.
2. Playtest; confirm the fresh run contains the edits.
3. Confirm normal camera, movement, combat, damage, edited-ground collision.
4. Press F8; confirm undo/redo/save still work.
5. Repeat playtest; test an unrelated run to catch stale-session reuse.
6. Confirm leaderboard/achievement/stats writes are suppressed during playtest.

## Finish
- Update docs/development.md (playtest controls, harness notes) and user controls docs.
- `task check`.
- Record evidence + plan in Backlog; conventional commit, no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
LevelLoaderPatch: extracted Start(LevelFile, logger) -> bool; LoadAndStart now deserializes and delegates. Both existing callers ignore the return, so no behavior change. Reusing this path arms the custom-run guard, so the TASK-004.04 leaderboard/achievement/stats suppression is active during playtest.

editor_session_pick.cs (new, Unity-free): EditorSessionPick.Pick - a preserved playtest session wins; otherwise a fresh EditSession when generation changed or session is null, matching the original OnEditorEntered behavior.

editor_playtest_coordinator.cs (new, Unity-free): PlaytestCoordinator captures the editor EditSession plus lastSavedEditCount at Playtest start; TryRestore returns it on F8 return; Discard clears it on failed start.

editor_tile_tools.cs: Playtest(logger) builds SnapshotLevelFile(_session.CurrentEdits), captures the session, starts via LevelLoaderPatch.Start, clears invulnerability, exits editor mode; on failure it discards and toasts leaving history intact. Added a Playtest toolbar button (disabled when no live session). OnEditorEntered now restores via EditorSessionPick.Pick.

Tests: editor_playtest_tests.cs (8 tests) covering CurrentEdits excludes undone ops, coordinator restore/discard, pick restore/reset/keep-after-discard. All 686 tests pass; mod builds clean with 0 warnings.

docs/development.md: toolbar controls table Playtest row plus a full playtest paragraph (in-memory LevelFile, guard active, session preserved, invulnerability cleared).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Playtest action added to the editor toolbar. It builds a LevelFile from the editor's in-memory edit list (SnapshotLevelFile), starts a fresh run via the new LevelLoaderPatch.Start(LevelFile, logger) entry point, clears invulnerability, and exits editor mode. Returning to the editor on F8 restores the preserved undo/redo session (PlaytestCoordinator + EditorSessionPick.Pick) instead of resetting on the generation change. Because Start reuses the disk-load path (seed forcing, SetPendingEdits, CustomLevelState.MarkPendingStart), the TASK-004.04 custom-run guard arms automatically, so leaderboard/achievement/stats writes stay suppressed during playtest.

Verification (dev harness, example-forest): raised tile (10,7), Playtest -> fresh run with the raised platform visible, player vulnerable with normal HUD/enemies, 68 SteamWriteGuard suppressions during the run; F8 returned to editor with the session intact, and Ctrl+Z/Ctrl+Y both worked.

Tests: 8 new tests in editor_playtest_tests.cs (Unity-free coordinator + session-pick logic); 686 total pass. Mod builds clean (0 warnings). task check (build + test + lint) passes. docs/development.md updated (toolbar row + playtest paragraph). Commit 8fce8e4.
<!-- SECTION:FINAL_SUMMARY:END -->
