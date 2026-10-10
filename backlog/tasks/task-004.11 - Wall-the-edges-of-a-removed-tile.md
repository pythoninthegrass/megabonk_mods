---
id: TASK-004.11
title: Wall the edges of a removed tile
status: To Do
assignee: []
created_date: '2026-10-10 06:41'
labels:
  - level-editor
dependencies: []
references:
  - src/MegabonkLevels.Mod/fill_edge_plan.cs
  - src/MegabonkLevels.Mod/fill_regeneration.cs
  - docs/runtime-map-structure.md
  - levels/task-004-05-regression.mblevel.json
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

Lance saw this in the game on 2026-10-10 by removing the generated-then-edited East slope at Forest (9,7) (seed 20261007, `levels/task-004-05-regression.mblevel.json` loaded). The regression level's (13,7) hole looked closed in TASK-004.05 only because its neighbours already had walls from generation.

Likely fix (unconfirmed): for each edge between a removed cell and an occupied neighbour, destroy the fill pieces on that edge, then build the neighbour's wall down into the hole. The private `ProceduralTileGeneration.FillEdge(Vector2Int pos1, int desiredHeightOffset, bool isFacingOut, Vector2Int dir, bool useEdgeTextures)` is probably what generation uses for the map's outer cliffs. Its parameter meanings are unknown: work them out from the native code (Binary Ninja, RVA in .tools/il2cpp_dump/dump.cs) or by experiment in the game. `FillHole` already handles occupied-to-occupied edges.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Removing a tile (flat or slope) leaves no wall or fill piece of that tile in its cell
- [ ] #2 Every occupied neighbour of a removed cell shows a wall facing into the hole, with no sky visible past the neighbour's edge, confirmed with screenshots in the game
- [ ] #3 The same result holds for a removal from a level file at load and from the editor's Remove tool
- [ ] #4 Ground collision still has no floor over the removed cell after the rebuild
- [ ] #5 Pure edge-selection logic is unit tested; docs/runtime-map-structure.md "Walls after edits" documents the FillEdge parameters as confirmed
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
