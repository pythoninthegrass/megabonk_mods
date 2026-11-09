---
id: TASK-005.04
title: 'Object editing tools (place, move, rotate, delete) with grid snap'
status: Done
assignee:
  - '@claude'
created_date: '2026-10-06 21:43'
updated_date: '2026-11-09 05:26'
labels:
  - level-editor
dependencies:
  - TASK-005.02
parent_task_id: TASK-005
priority: high
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005 first for full context.

Implement object placement/manipulation tools: place the currently-selected palette item (from TASK-005.02) at the cursor's world position, move an existing placed/generated object by pressing and dragging it, rotate it, and delete it. Each action constructs the corresponding TASK-003.02 op (`PlaceObject`, `MoveObject`, `RemoveObject`) with the correct `catalogId`/`genId`/placement-id target, pushes it through the `EditStack`, and applies it live via TASK-004.02's logic.

Placement is not snapped: it uses the cursor's ground point clamped to the targeted cell, with tile spacing and height read from `StageData.mapParameters` (same source TASK-004.02 uses). The original grid-snap requirement was dropped after in-game testing; see the implementation notes.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The selected palette item is placed at the cursor's ground point, clamped to the targeted cell and set at the tile surface there (ramp-aware); not snapped to cell centres or a grid. A quarter-tile grid and an orange ring are drawn as visual guides only, and an identical prefab at the exact same position is refused
- [x] #2 An existing object (generator-spawned or editor-placed) is selected by pressing it, moved by holding 0.2 seconds and dragging, and rotated in 90 degree yaw steps with R and Shift+R; pitch and roll are split out to TASK-005.09
- [x] #3 An existing object can be deleted with Delete or Backspace
- [x] #4 Each action constructs the correct TASK-003.02 op with the correct target (catalogId for new placements, genId or placement id for existing objects) and applies it through EditStack and TASK-004.02's live-application logic
- [x] #5 Middle-clicking an existing object selects its catalog entry in the palette (pick block), preferring the current stage's entry and scrolling the palette to it; an object with no matching entry is reported, not guessed
- [x] #6 A newly placed object faces the camera: its yaw is the camera's yaw plus 180 degrees, rounded to the nearest 90
- [x] #7 The selected object shows a red ring on the ground beneath it, centred on its origin and sized from its mesh renderers; tiles, tile objects and particle-only roots such as ForestParticles are never selectable
- [x] #8 The editor opens on the Select tool with an overview camera (40 degrees down, behind the player), so the first click edits nothing
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Decisions (the maintainer, 2026-10-10):
- Picking an existing object: a physics raycast whose hit root resolves to an indexed object first; if nothing is hit, the indexed object nearest the cursor's ground point within half a tile (XZ distance). Tiles, walls and fill pieces (tile/flatTile/fillTile) are never picked. Log which path picked it.
- Rotation: 90 degree yaw steps; R clockwise, Shift+R counter-clockwise; pitch and roll are kept.
- Snap: always on, to cell centres. Y = the cell's surface (Height * tileHeight, plus half a level on a ramp). No toggle (YAGNI).
- Workflow: 5 Place, 6 Select. Select: click an object to select it (footprint outline); click the ground to move it there, snapped; R/Shift+R rotate; Delete or Backspace remove; clicking the selected object again deselects. No drag.
- Minecraft creative mode (native and the Better Creative Mode mods) reviewed: not substituted, because one block per cell lets Minecraft treat a move as break plus place, which here would lose genIds; the crosshair, right-click place and hotbar clash with right-click look and the digit tool hotkeys. Two ideas adopted as ACs: middle-click pick block, and new objects facing the camera.

Pure logic (TDD, compile-linked into tests):
1. Rename TileTool -> EditorTool, adding Place and Select; move FromHotkey (5, 6) and ToolbarText into editor_tool.cs. The toolbar's second line depends on the tool: tile target / place cell plus selected catalog item (or a prompt to pick one) / hovered or selected object name plus target. TileTools.Build keeps handling only the tile tools.
2. Extract the shared cell-centre maths (grid-centred, same origin as PositionReadout.CellOf) and use it from TileOutline and the snap code.
3. object_tool.cs: SnapPosition(cell, TileState, grid); FacingYaw(cameraYaw) = round((cameraYaw + 180) / 90) * 90 mod 360; Place(catalogId, position, rotation, scale) -> PlaceObject op (rotation = prefab pitch/roll with facing yaw, scale = prefab localScale); Move(target, current transform, position) keeps rotation and scale; Rotate(target, current transform, clockwise) yaw +/-90 normalised to [0, 360); Remove(target).
4. object_picker.cs: nearest candidate within a max XZ distance.
5. palette_pick.cs: given palette entries, a prefab name (genId category after "object:", or a placed object's catalogId directly) and the current stage, return the matching entry, preferring the current stage, else stage-independent entries, else null.
6. Tests for the above plus a planner round trip for PlaceObject/MoveObject/RemoveObject (placement ids allocated in order, MoveObject on a placement keeps its catalogId).

Live side:
7. LiveEditPatch/Applier: reverse lookup GameObject -> ObjectTarget over the pickable genId categories (tileObject, object:*) and placed objects; ObjectFor(target); pickable objects for the fallback picker; prefab lookup by catalogId (CatalogPrefabs) for scale/rotation; the current stage index (currentStage against the map's stages) for pick block.
8. editor_object_tools.cs: input, picking, selection footprint outline (second LineRenderer in a different colour, from combined Renderer bounds), place preview reusing the tile outline, middle-click pick block (selects the palette entry and switches to Place). EditorTileTools keeps the toolbar and hands Place/Select over. Wire into EditorMode. Ignore clicks while EditorPalette.PointerOverPanel.

Docs: development.md "Object tools" section; level-format.md on editor-made object ops and their targets; runtime-map-structure.md on whether objects have colliders (learned in game).

Verification: task check (tests fail first, then pass); regression level LiveEdit log lines unchanged; in game (the maintainer drives the mouse) on Forest: place, select, move, rotate, delete, pick block and camera facing for one generated and one placed object, with screenshots and logs; confirm R, Delete, Backspace and middle click trigger no game action.

Risks and limits:
- The applier destroys a removed object, so undo in TASK-005.05 must respawn it or removal must switch to deactivation; left to TASK-005.05.
- Moving an object carries its own collider; objects are not part of the baked ground mesh, so no collision rebuild.
- Placed objects are bare prefab instances; spawner-side initialisation was only proven for the chest (TASK-004.02).
- Which way a prefab's front points (+Z assumed) for camera facing is unconfirmed; check in game.
- Pick block matches by prefab name; tile objects may have no catalog entry, and duplicate names across stages fall back to the current stage.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10: pure logic done with tests (EditorTool/EditorTools in editor_tool.cs, ObjectTools, ObjectPicker, PalettePick, PositionReadout.CellCentre); task mod:test 443 passing. Next: live side (LiveEditPatch lookups, EditorObjectTools input/picking/outline), docs, in-game check.

2026-10-10: live side written (LiveEditPatch.TargetOf/ObjectFor/PickableObjects/CatalogIdOf/PrefabFor/CurrentStageIndex, editor_object_tools.cs, EditorTileTools hands tools 5/6 over) and docs/development.md + level-format.md updated; task check passes (443 tests, build, lint). Not yet verified in the running game; ACs stay unchecked until the maintainer drives place, select, move, rotate, delete, pick block and camera facing on Forest. Open in-game questions: do tile objects and trees have colliders (raycast vs nearest path), which way a prefab front points, do R/Delete/Backspace/middle click trigger a game action.

2026-10-10: the maintainer's first in-game pass: placement snapped to cell centres only, so one object per cell, and identical objects stacked on the same spot (11 Tree0 at cell (10,8)), which made a stacked tree look undeletable; pick block did not reveal the palette entry when it was off screen. Changed: snap to a quarter-tile grid (spacing / 4, intersections include the centre) with a thin grid overlay and snap marker, ramp height follows the surface; placing or moving an identical prefab to the same position is blocked, different objects may share a position; the palette scrolls to the picked entry; the toolbar widened to 960x80 because tool 6 was ellipsised. Out of scope for this task: finer than quarter tile, which could later be added by holding Alt/Option. Not yet re-verified in game.

2026-10-10: the maintainer found the quarter-tile snap too rigid. Placement and move now use the cursor's ground point unsnapped, clamped to the targeted cell, at the tile surface there (ObjectTools.PositionAt replaces SnapPosition); the quarter-tile grid lines stay as a visual guide and the orange marker shows the exact point. This supersedes the earlier snap decisions (cell centres, then quarter tile), and the Alt/Option finer-step idea no longer applies. Stacking is still blocked, but now only catches an exact repeat at the same coordinates. task check passes (460 tests).

2026-10-10: the maintainer reported move did nothing: clicking the ground deselected a selected chest. Cause: Select ran the pick (raycast, then nearest object within half a tile) on every click, so a ground click near any object picked or deselected it before the move code ran. Replaced click-to-move with press-and-drag: press selects and picks up, the object follows the cursor as a preview, release makes one MoveObject (reverted without an edit over the palette, off the grid, onto an identical object, or with no movement); a generated object keeps its own height above the surface. Pressing on nothing deselects; pressing the selected object no longer toggles it off. task check passes (464 tests). Not yet verified in game.

2026-10-10: the maintainer asked for a hold threshold so a quick click on an object only selects it. A press now becomes a drag after 0.2 seconds held (ObjectTools.DragStarted, unscaled time); the dragged object keeps the offset at which it was grabbed instead of jumping to the cursor. the maintainer also wants 3D rotation (pitch and roll, not only yaw): split out as TASK-005.09. task check passes (468 tests). Not yet verified in game.

2026-10-10: the maintainer asked for the selection cursor to be a circle snapped beneath the object, as in RTS/MOBA games, resizing with the object. The cyan box is replaced by a red ring (ObjectTools.Ring, 48 segments) centred on the object's renderer bounds at its base, radius the larger horizontal half-extent; the orange placement marker is also a ring and shows only in Place. task check passes (470 tests). Not yet verified in game.

2026-10-10: the editor now opens on Select (EditorTools.Default) on every entry instead of Raise, so the first click on the map cannot raise a tile; the last tool is no longer kept across entries. task check passes (471 tests). Not yet verified in game.

2026-10-10: tileObject genIds (ForestParticles and similar scenery) are no longer pickable, so they are never selected, dragged or ringed; only object:* generator spawns and editor-placed objects are (ObjectTools.IsPickableGenId, shared by the reverse lookup and the nearest-object fallback). task check passes (477 tests). Not yet verified in game.

2026-10-10: in-game, ForestParticles was still selectable and the ring was far too large (a tall tree's ring covered a smaller one). ForestParticles is an object:* scene root, not a tileObject, so it is now unpickable because it has no non-particle renderer (HasMeshRenderer; csproj gained UnityEngine.ParticleSystemModule). The ring is now centred on the object's origin (the trunk, not the canopy bounds), at the bounds' base, with radius 40% of the larger half-extent of its mesh renderers (particle renderers ignored). Not yet verified in game; the 0.4 factor is a guess to tune.

2026-10-10: the editor camera now starts as a fixed overview of the player (FreeFlyCamera.OverviewPose: 60 units up, back along +Z, pitch 40, yaw 180) instead of the game camera's pose, matching the maintainer's screenshots. The pose is estimated from those screenshots, not measured (height, back distance and pitch are the tunables). task check passes (478 tests). Not yet verified in game.

2026-10-10: the maintainer confirmed in game that placing, selecting, dragging, rotating, deleting, pick block, camera facing, the rings and the Select default with overview camera all work after the quality-of-life and grid changes. Open defects found while verifying are tracked in TASK-005.04.01 (no ring for ChargeShrines, broken chest rings, Forest ruins not selectable); 3D rotation is TASK-005.09; undo of a removed object is TASK-005.05.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Object tools for the editor: Place (tool 5) puts the selected palette item at the cursor's ground point, clamped to the targeted cell at the tile surface, facing the camera; Select (tool 6, the default on entry) selects an object by pressing it, drags it after a 0.2 second hold, rotates it in 90 degree yaw steps (R, Shift+R) and deletes it (Delete, Backspace); middle click picks the object's palette entry. Every action builds a PlaceObject, MoveObject or RemoveObject op, pushes it through EditStack and applies it live. Grid snapping was dropped during in-game testing in favour of an unsnapped point with a quarter-tile guide grid; identical prefabs at the exact same position are refused. A red ring beneath the selected object shows the selection, tiles, tile objects and particle-only roots are not selectable, and the editor starts on an overview camera. Known defects are in TASK-005.04.01, pitch and roll rotation in TASK-005.09, and undo of removal in TASK-005.05. Tests were written first for the pure logic, except the overview pose test, which was added together with its code.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
