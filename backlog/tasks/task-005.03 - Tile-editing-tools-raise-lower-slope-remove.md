---
id: TASK-005.03
title: 'Tile editing tools (raise, lower, slope, remove)'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-06 21:43'
updated_date: '2026-10-10 06:43'
labels:
  - level-editor
dependencies:
  - TASK-005.01
parent_task_id: TASK-005
priority: high
ordinal: 25000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005 first for full context.

Implement mouse-driven tile tools while in editor mode: raise, lower, rotate-slope, and remove, operating on the tile the player's cursor/raycast is over. Each tool action should construct the corresponding TASK-003.02 edit op (`SetTileHeight`, `SetTileSlope`, `RemoveTile`, `AddTile`) and push it through TASK-003.03's `EditStack`, then apply it live using TASK-004.02's live-application logic (reuse directly — do not reimplement tile mutation logic in UI code) so the change is immediately visible.

Include basic tool-mode UI (a toolbar or hotkeys to switch between raise/lower/slope/remove) and a visible cursor/highlight showing which tile is currently targeted.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Raise, lower, slope-rotate, and remove tools are selectable and operate on the tile under the player's cursor via raycast
- [x] #2 Each tool action constructs the correct TASK-003.02 edit op and applies it through TASK-003.03's EditStack and TASK-004.02's live-application logic
- [x] #3 Changes are immediately visible in the 3D view when a tool is used
- [x] #4 A visible highlight indicates which tile is currently targeted before an action is taken
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Decisions (Lance, 2026-10-10):
- Baseline: EditStack/LiveEditPlan replayed on an empty LevelState, so SetTileHeight on an untouched cell dropped its slope and SetTileSlope reset its height to 0. Seed a baseline LevelState from the generated grid (snapshot before file edits run) and replay on top of it, both at load time and in the editor. ReachabilityValidator already treats LevelState as the full grid.
- Slope tool cycles None -> North -> East -> South -> West -> None.
- Lower stops at level 0 (no op emitted at 0).
- No Add tool (removed cells can't be raycast; undo in TASK-005.05 restores them).

Pure logic (TDD, compile-linked into tests):
1. level_state.cs: LevelState.FromTiles(tiles) factory (fresh copy; EditStack mutates its state).
2. live_edit_plan.cs: extract LiveEditPlanner (EditStack + nextPlacementId, Apply(op) -> LiveAction, State). LiveEditPlan.Build(edits, baseline) uses it. Update existing tests.
3. tile_tool.cs: TileTool {Raise, Lower, Slope, Remove}; TileTools.NextSlope, TileTools.Build(tool, x, z, current) -> EditOp?, TileTools.FromHotkey(1-4).
4. tile_outline.cs: TileOutline.Corners(x, z, state, width, depth, spacing, tileHeight, lift) -> 4 world corners of the top surface, same centred origin as PositionReadout.CellOf; slope uphill edge at h+1.
5. Tests: tile_tool_tests, tile_outline_tests, live_edit_plan baseline cases (setHeight keeps slope, setSlope keeps height, baseline not mutated, planner incremental == Build), LevelState factory test; csproj Compile links.

Live side:
6. live_edit_patch.cs: snapshot baseline from proceduralTiles in OnGenerationComplete (posY, slope from isFlat/dir); Build(edits, baseline); keep a static session (Applier, index, planner seeded with baseline then file edits) for every Tiles generation, vanilla included; ApplyLive(EditOp); extract RefreshTerrain(touched) shared with ApplyEdits; expose TileAt and grid parameters/ground MeshCollider.
7. editor_ui.cs: move NewRect/NewLabel/Stretch from editor_palette.cs into shared EditorUi.
8. editor_tile_tools.cs: toolbar label (top centre: tools, current tool, target cell/height/slope) and LineRenderer highlight (Sprites/Default, fallback Hidden/Internal-Colored; verify in game). Tick: digits 1-4 switch tool; skip when PointerOverPanel; ray ScreenPointToRay -> ground MeshCollider.Raycast; cell = CellOf(hit.point - hit.normal*0.01); highlight; left click -> TileTools.Build -> LiveEditPatch.ApplyLive; log.
9. editor_mode.cs: wire Tick and enter/exit hooks.

Docs: development.md "Tile tools" section; level-format.md baseline semantics; runtime-map-structure.md per-click collision rebuild + raycast note.

Verification: task check (tests fail first, then pass); regression level LiveEdit log lines unchanged before/after; in-game tool clicks with screenshots and logs (mouse needs a person/KVM/osascript); confirm digits 1-4 don't trigger game actions while paused.

Revisions after in-game testing (Lance, 2026-10-10): generated Forest heights run from -3 to 2, so Lower stops at the map's lowest generated level (LiveGrid.LowestLevel), not 0. The baseline changed how levels/task-004-05-regression.mblevel.json loads ((10,5) generated West slope, (9,7) generated North slope at -1); pinned with setSlope (10,5) None and setHeight (9,7) 0 so it loads as verified in TASK-004.05 (9 edits). Missing walls around removed tiles is a FillRegeneration gap, tracked as TASK-004.11.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10: Pure logic (LevelState.FromTiles, LiveEditPlanner + baseline Build, TileTools incl. ToolbarText, TileOutline) written test-first; 395 tests pass, task check green. Live side: LiveEditPatch keeps a Session (applier, planner on generated baseline) per Tiles generation and exposes ApplyLive/TileAt/Grid/GroundCollider; ApplyPlan shares fill regeneration + collision rebuild between load and live edits. EditorUi holds the UGUI helpers moved out of EditorPalette. EditorTileTools draws the toolbar and a LineRenderer outline. Docs updated (development.md Tile tools, level-format.md baseline semantics, runtime-map-structure.md). In-game verification pending.

2026-10-10 in-game: regression level loads with (9,7) East slope at level 0 at (80,0,0) and (10,5) flat at level 1, matching the pre-change result; FillRegeneration/CollisionRebuild/KillFloor clean. Toolbar renders and the raycast targets the correct cell and state; highlight shader Sprites/Default. Lance drove raise, lower, slope cycling and remove by mouse and reported it looks good, with one problem: removing the (9,7) slope leaves sky visible under it because FillEdgePlan skips removed cells (TASK-004.11). A removed cell is untargetable by design until undo (TASK-005.05). Forest palette: 75 entries.

2026-10-10 (Lance): keys 1-4 do nothing in normal play, so no game binding collides with the tool hotkeys; a tool click on Forest (about 600 collision pieces) is instant.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Adds mouse-driven tile tools to editor mode: Raise, Lower, Slope and Remove, selected with keys 1-4. They act on the tile under the pointer, which is outlined. A click builds the TASK-003.02 op and applies it live through the same planner, applier, fill regeneration and collision rebuild that level files use at load.

Changes:
- Tile ops now replay on top of the generated grid instead of an empty LevelState. `LiveEditPatch` snapshots `proceduralTiles` at generation, and `LiveEditPlan.Build(edits, baseline)` / `LiveEditPlanner` replay on a copy of it, so SetTileHeight keeps a cell's generated slope and SetTileSlope keeps its generated height. `LevelState.FromTiles` builds the copies.
- `LiveEditPatch` keeps a per-generation session (applier, planner, grid parameters) for every Tiles map. It exposes `ApplyLive`, `TileAt`, `Grid` and `GroundCollider`, and batch and live application share `ApplyPlan`.
- `tile_tool.cs` (what each tool emits: Lower stops at the map's lowest generated level, Slope cycles N/E/S/W/flat; also the toolbar text and hotkeys) and `tile_outline.cs` (outline corners on the centred grid, ramp-aware) are pure logic and tested.
- `EditorTileTools` raycasts against the baked ground collision only and draws a toolbar and a LineRenderer highlight. `EditorUi` holds the UGUI helpers moved out of `EditorPalette`.
- `levels/task-004-05-regression.mblevel.json` gains two pinning edits so it loads exactly as verified before the baseline change.
- Docs: development.md "Tile tools", level-format.md baseline semantics and the corrected regression table, runtime-map-structure.md per-click rebuild note.

Tests: 396 unit tests pass (`task check`). New tests cover the tools, outline, toolbar text, LevelState.FromTiles, baseline replay and planner/Build equivalence. In the game: the regression level loads with the same final tile states as before, the toolbar and targeting work, and Lance clicked through every tool.

Follow-ups: TASK-004.11 (walls around removed tiles; sky shows under a removed tile today). Undo of removals arrives with TASK-005.05. Not confirmed: that keys 1-4 trigger no game action while paused (no report either way), and the cost of a click on larger maps (each click rebuilds the full collision mesh, about 600 pieces on Forest).

Confirmed afterwards by Lance: keys 1-4 have no game binding (they do nothing in normal play), and a click is instant on Forest.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
