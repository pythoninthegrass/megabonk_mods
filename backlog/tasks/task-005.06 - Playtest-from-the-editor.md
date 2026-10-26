---
id: TASK-005.06
title: Playtest from the editor
status: In Progress
assignee:
  - '@Assistant'
created_date: '2026-10-06 21:43'
updated_date: '2026-10-26T17:21:00Z'
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
F8 is the single toggle between frozen in-game editing and live playtesting of the same run. Edits already apply live; do not restart the stage or require saving. Remove the separate Playtest button and restart-specific session restoration. Preserve unsaved edits, undo/redo and save bookkeeping across toggles; resume the normal player camera/gameplay. Any run entered into the editor must remain excluded from leaderboard, achievement and stats writes until a new normal run starts. User approved replacing the original fresh-run playtest contract with same-run continuation (player position, health, enemies and timer retained).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 F8 alternates editing and live gameplay in the same run with current unsaved edits, without a Playtest button or stage reload
- [ ] #2 Repeated F8 toggles preserve undo/redo and save state and restore the normal follow camera, movement and combat
- [x] #3 Editor-used runs suppress leaderboard/achievement/stats writes until a new normal run starts
- [x] #4 Raised/lowered statically batched tiles have visible ground at the edited height matching collision, including undo/redo and live F8 playtests
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
1. Write regression tests for sticky editor-used scoring guard and same-generation edit session selection.
2. Remove Playtest toolbar action and restart-specific coordinator; retain F8's same-run exit/entry and generation-based session reset.
3. Mark the current run custom/unscored on editor entry, preserving guard until next run.
4. Update controls docs; run task check.
5. Rebuild/relaunch via harness and verify repeated F8 transitions, raised/enclosed terrain, camera follow, undo/redo, gameplay and scoring guard. Record actual evidence; do not claim unverified behavior.

User approved including missing-ground fix. Live TileRender diagnostics confirmed staticBatch=True and render bounds remaining at y=-20 after transform moved to y=0. Add Unity-free placement-policy tests, replace batched tiles instead of moving them, remove temporary diagnostics, verify surface/collision at edited height plus undo/redo and enclosed terrain.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
LevelLoaderPatch: extracted Start(LevelFile, logger) -> bool; LoadAndStart now deserializes and delegates. Both existing callers ignore the return, so no behavior change. Reusing this path arms the custom-run guard, so the TASK-004.04 leaderboard/achievement/stats suppression is active during playtest.

editor_session_pick.cs (new, Unity-free): EditorSessionPick.Pick - a preserved playtest session wins; otherwise a fresh EditSession when generation changed or session is null, matching the original OnEditorEntered behavior.

editor_playtest_coordinator.cs (new, Unity-free): PlaytestCoordinator captures the editor EditSession plus lastSavedEditCount at Playtest start; TryRestore returns it on F8 return; Discard clears it on failed start.

editor_tile_tools.cs: Playtest(logger) builds SnapshotLevelFile(_session.CurrentEdits), captures the session, starts via LevelLoaderPatch.Start, clears invulnerability, exits editor mode; on failure it discards and toasts leaving history intact. Added a Playtest toolbar button (disabled when no live session). OnEditorEntered now restores via EditorSessionPick.Pick.

Tests: editor_playtest_tests.cs (8 tests) covering CurrentEdits excludes undone ops, coordinator restore/discard, pick restore/reset/keep-after-discard. All 686 tests pass; mod builds clean with 0 warnings.

docs/development.md: toolbar controls table Playtest row plus a full playtest paragraph (in-memory LevelFile, guard active, session preserved, invulnerability cleared).

## Regression discovered post-merge: playtest camera does not revert to the follow camera

After the task was marked Done, a regression was reported and is under investigation:
hitting Playtest leaves the gameplay camera stuck instead of reverting to the game's
follow camera that tracks Tony. The user confirmed this is the real bug, distinct from
the black window and from the fall.

Dev-harness findings so far:
- Camera DOES follow Tony after recovery (teleport to a distant cell keeps the view centered on the player).
- No fall reproduces on normal terrain — player rests at spawn Y≈1.925 (feet at transform.position.y - 1.925).
- The ~1.6s black window at playtest start is the in-place reload window (StartNewMap → A_GenerationComplete), NOT the camera stuck in terrain.
- F8 return-to-editor still works correctly (editor=true, run frozen, palette intact, 75 entries) — unaffected.
- Playtest handoff order: Playtest() → LevelLoaderPatch.Start → StartNewMap → PlayerInvulnerability.Set(false) → EditorMode.Set(false)/Exit → CameraOverride.Clear().
- CameraOverride.Clear() reverts to the game default (saves the game follow pose before the first override, restores on exit) and fires at t=0, ~1.6s BEFORE A_GenerationComplete — the restore lands mid-recreation, which is the suspected handoff failure.

Still open: reproduce with the user's exact repro (modified terrain — plateau or a 4-wall pit). Load a level file with the modification, playtest, and watch the camera immediately after recovery. The 5×5 level-1 plateau test spawned the player at Y=-1.75 (below the raised surface), so spawn position is terrain-sensitive. Fix scope is the camera handoff only — no terrain/spawn/loading-screen work.

User approved revised same-run F8 contract. Existing task file has pre-existing local investigation notes; retaining them. Unrelated untracked task and scratch levels are left untouched.

First live F8 round-trip found editor auto-entry can precede generation complete, leaving a stale session generation. Added SynchronizeSession on editor ticks so the new generation is adopted before accepting edits; retest preserved dirty state and undo/redo. Terrain rendering also failed: moved batched tile collider follows transform but render bounds stay at original height. User explicitly approved including terrain rendering fix.

Implemented F8-only same-run playtesting: removed Playtest toolbar action and PlaytestCoordinator, retained same-run history/save bookkeeping, reset only on run generation changes. Editor entry immediately marks current run unscored; no exit path clears it. Batched tile renderers now trigger prefab replacement, while subsequent unbatched height changes can move directly. Temporary TileRender diagnostics removed.

Verification: task check passes (690 C# tests, 185 Python tests, markdownlint/ruff); mod builds with zero warnings. Regression tests written before new APIs. Live MCP: two unsaved raises at (9,6), F8 play and return, undo lowered surface, redo raised it again, subsequent F8 cycles retained dirty count/history. Logs show one map-generation/index event, no reload between toggles. Player on raised level-1 surface stable at body y=21.925 with visible grass underneath. Evidence: .tools/evidence/megabonk-1793034950591766000.png (live platform), megabonk-1793034965676706000.png (undo with dirty 1/redo ready).

Enclosed-pit test: .tools/evidence/f8-pit.mblevel.json raises four neighbors of (10,7) to level 3, with center level 0. F8 restored normal camera inside pit, visible floor/walls, player stable at y=1.925; teleport within pit and repeated F8 succeeded. Evidence: .tools/evidence/megabonk-1793035026994706000.png. New run replaced previous dirty edit history with 5 saved seed edits. SteamWriteGuard suppressions observed during gameplay; unit tests confirm editor-used normal runs are guarded immediately and next normal run clears guard. No game errors/exceptions during final pit test.

AC2 left unchecked pending hands-on normal keyboard movement/damage review: harness keys drive editor input only, not Rewired gameplay movement. Camera/freeze, terrain physics, combat/enemy activity, same-run persistence and undo/redo verified live; save bookkeeping verified in unit tests. Final handoff: fresh example forest in editor, unsaved raised platform at (9,6), player on platform, harness invulnerability disabled. Press F8 to walk/test damage and F8 again to edit. Task remains In Progress rather than declaring untested interaction complete.

Implementation committed as 0e2b50a (fix(editor): use F8 live playtests and replace batched terrain). Task remains In Progress pending hands-on AC2 review, not a known failing automated check.
<!-- SECTION:NOTES:END -->
