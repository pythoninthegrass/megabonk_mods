---
id: TASK-005.04
title: 'Object editing tools (place, move, rotate, delete) with grid snap'
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-06 21:43'
updated_date: '2026-10-10 07:01'
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

Implement object placement/manipulation tools: place the currently-selected palette item (from TASK-005.02) at the cursor's world position with grid snapping, move an existing placed/generated object (by clicking and dragging, or click-to-select then click-to-reposition), rotate it, and delete it. Each action constructs the corresponding TASK-003.02 op (`PlaceObject`, `MoveObject`, `RemoveObject`) with the correct `catalogId`/`genId`/placement-id target, pushes it through the `EditStack`, and applies it live via TASK-004.02's logic.

Grid snapping should align to the tile grid spacing from `StageData.mapParameters` (same source TASK-004.02 uses — do not hardcode a separate snap value).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The currently-selected palette item can be placed at the cursor's world position with grid snapping aligned to StageData.mapParameters's tile spacing
- [ ] #2 An existing object (generator-spawned or editor-placed) can be selected, moved, and rotated
- [ ] #3 An existing object can be deleted
- [ ] #4 Each action constructs the correct TASK-003.02 op with correct target reference (catalogId for new placements, genId or placement-id for existing objects) and applies it through EditStack + TASK-004.02's live-application logic
- [ ] #5 Middle-clicking an existing object (generator-spawned or editor-placed) selects its catalog entry in the palette (pick block), preferring the current stage's entry; an object with no matching entry is reported, not guessed
- [ ] #6 A newly placed object faces the camera: its yaw is the camera's yaw plus 180 degrees, rounded to the nearest 90
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Decisions (Lance, 2026-10-10):
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

Verification: task check (tests fail first, then pass); regression level LiveEdit log lines unchanged; in game (Lance drives the mouse) on Forest: place, select, move, rotate, delete, pick block and camera facing for one generated and one placed object, with screenshots and logs; confirm R, Delete, Backspace and middle click trigger no game action.

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

2026-10-10: live side written (LiveEditPatch.TargetOf/ObjectFor/PickableObjects/CatalogIdOf/PrefabFor/CurrentStageIndex, editor_object_tools.cs, EditorTileTools hands tools 5/6 over) and docs/development.md + level-format.md updated; task check passes (443 tests, build, lint). Not yet verified in the running game; ACs stay unchecked until Lance drives place, select, move, rotate, delete, pick block and camera facing on Forest. Open in-game questions: do tile objects and trees have colliders (raycast vs nearest path), which way a prefab front points, do R/Delete/Backspace/middle click trigger a game action.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
