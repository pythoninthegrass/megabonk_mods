---
id: TASK-004.11
title: Wall the edges of a removed tile
status: Done
assignee: []
created_date: '2026-10-10 06:41'
updated_date: '2026-11-09 05:26'
labels:
  - level-editor
dependencies: []
references:
  - src/MegabonkLevels.Mod/fill_edge_plan.cs
  - src/MegabonkLevels.Mod/fill_regeneration.cs
  - docs/runtime-map-structure.md
  - levels/task-004-05-regression.mblevel.json
  - levels/removed-tile-regression.mblevel.json
modified_files:
  - src/MegabonkLevels.Mod/fill_edge_plan.cs
  - src/MegabonkLevels.Mod/fill_regeneration.cs
  - src/MegabonkLevels.Mod/live_edit_patch.cs
  - tests/MegabonkLevels.Tests/fill_edge_plan_tests.cs
  - docs/runtime-map-structure.md
  - levels/removed-tile-regression.mblevel.json
parent_task_id: TASK-004
priority: high
ordinal: 49000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read docs/runtime-map-structure.md ("Walls after edits", "Ground collision after edits") first.

When a tile is removed, by a level file's `tile.remove` or by the editor's Remove tool (TASK-005.03), `FillRegeneration` does nothing around it. `FillEdgePlan.EdgesAround` skips a touched cell that is now empty, and the log shows `FillRegeneration: 0 edge(s), removed 0 stale piece(s)`. Two things go wrong:
- The removed tile's own wall and fill pieces stay in place. A removed slope leaves its side walls hanging.
- Occupied neighbours get no wall facing down into the hole, so the player sees past their edges to the sky below the map.

the maintainer saw this in the game on 2026-10-10 by removing the generated-then-edited East slope at Forest (9,7) (seed 20261007, `levels/task-004-05-regression.mblevel.json` loaded). The regression level's (13,7) hole looked closed in TASK-004.05 only because its neighbours already had walls from generation.

Likely fix (unconfirmed): for each edge between a removed cell and an occupied neighbour, destroy the fill pieces on that edge, then build the neighbour's wall down into the hole. The private `ProceduralTileGeneration.FillEdge(Vector2Int pos1, int desiredHeightOffset, bool isFacingOut, Vector2Int dir, bool useEdgeTextures)` is probably what generation uses for the map's outer cliffs. Its parameter meanings are unknown: work them out from the native code (Binary Ninja, RVA in .tools/il2cpp_dump/dump.cs) or by experiment in the game. `FillHole` already handles occupied-to-occupied edges.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Removing a tile (flat or slope) leaves no wall or fill piece of that tile in its cell
- [x] #2 Every occupied neighbour of a removed cell shows a wall facing into the hole, with no sky visible past the neighbour's edge, confirmed with screenshots in the game
- [x] #3 The same result holds for a removal from a level file at load and from the editor's Remove tool
- [x] #4 Ground collision still has no floor over the removed cell after the rebuild
- [x] #5 Pure edge-selection logic is unit tested; docs/runtime-map-structure.md "Walls after edits" documents the FillEdge parameters as confirmed
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Use REA/Ghidra findings: FillEdgesIsland calls FillEdge(cell, minPosY - 1 - tile.posY, true, outwardDirection, false). Do not derive depth from former removed-cell height (same-height removal would produce zero walls).
2. Write failing pure tests for hole-edge selection, cleanup of all touched edges including empty-empty/border edges, deduplication and downward-offset calculation. Keep existing occupied-edge API.
3. Include RemoveTile in touched terrain cells. Clean stale pieces using grid/world coordinates without dereferencing empty cells; rebuild occupied edges with FillHole and hole edges with FillEdge. Cover edits next to pre-existing holes and undo.
4. Build/relaunch through harness, verify flat/slope removals via level and editor, inspect walls/screenshots and downward collision rays.
5. Document confirmed FillEdge semantics, run task check, commit only task changes and finalize against evidence.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
REA/Ghidra decompiled FillEdge 0x18051DCC0, FillHole 0x18051F120, FillEdgesWalls 0x18051EAE0, FillEdgesIsland 0x18051E4D0 and FillEdges dispatcher. Island recipe confirmed: minimum grid posY minus 1 minus owning tile posY, facing-out true, outward cardinal direction, normal textures. Replaced earlier incorrect proposed depth based on removed-cell height. Artifacts: approved temporary opencode/rea directory (filledge.json, fillwalls.json, fillhole.json, filledgesisland.json).

TDD: added edge-selection/depth tests and ran task mod:test before implementation; failed with missing EdgesAroundRemovals/CleanupEdges/HoleWallOffset APIs. Implemented and reran successfully. Final task check passes: clean mod build, 679 C# tests, 165 Python tests, markdownlint and ruff. Existing unrelated test nullable warnings remain. git diff --check passes.

In-game evidence (Wine, Forest seed 20261007): original regression level load rebuilds 4 hole edges. Editor removal of edited East slope (9,7): removed 8 stale pieces, built 4 hole edges/15 pieces. Reproduced again with final DLL after removal of temporary diagnostics. Level fixture removes (9,7), (13,7), (0,0), (0,1): 11 hole edges, 44 pieces. Editor flat removal (11,6): 4 hole edges/15 pieces. Undo removes those 15 pieces and restores occupied edges; redo removes 4 pieces and rebuilds 15 hole pieces, without accumulation.

Temporary direct MeshCollider.Raycast probes after CollisionRebuild, from world y=200 down 500 units, returned combinedGroundHit=False over (9,7), (13,7), (0,0), (0,1) at load and (11,6) on editor removal/redo. Diagnostic code removed before final task check. Evidence saved locally in .tools/removed-tile-checks/: runtime-probes.log, editor-slope.png, final-editor-slope.png, editor-flat.png, load-slope.png, load-flat.png, load-border-pair.png, task-check.log. Screenshots inspected: continuous neighbour side walls, no hanging removed-slope side pieces, open shaft remains (sky at bottom is intentional; no floor). Generated props can overhang holes and are not terrain pieces.

Added permanent load-time regression fixture; documented FillEdge contract and removal/collision behavior. Game left frozen in editor on original regression level with slope (9,7) removed for inspection. Unrelated untracked TASK-015 left untouched. Honcho recall unavailable (HTTP 404 Session not found); continued without alternate memory store.

Implementation committed as c48ab00 (fix(terrain): rebuild walls around removed tiles), without attribution.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Removed tiles now participate in fill regeneration. Stale pieces are cleared even across adjacent holes or removed border cells, without dereferencing null tiles. Occupied neighbours receive downward FillEdge walls using the native island-cliff recipe confirmed through REA/Ghidra. Occupied-to-occupied FillHole behavior is preserved. Added pure regression tests, a load-time level fixture, and confirmed FillEdge documentation. Verified flat/slope removal from level files and editor, undo/redo, screenshots and no floor over holes after collision rebuilding. task check passes: 679 C# tests, 165 Python tests, build and lint. Implementation commit: c48ab00. Game remains frozen in editor for inspection.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
