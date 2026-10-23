---
id: TASK-005.04.01
title: 'Debug object selection rings and picking for shrines, chests and ruins'
status: In Progress
assignee:
  - Claude
created_date: '2026-10-10 08:11'
updated_date: '2026-10-23T02:44:00Z'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-005.04
priority: medium
ordinal: 51000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Found while verifying TASK-005.04 in the running game on Forest. Selection rings (ObjectTools.Ring, drawn by EditorObjectTools.RefreshOutline from the object's origin and its mesh renderer bounds) and picking (raycast, then nearest-object fallback, gated by ObjectTools.IsPickableGenId and LiveEditPatch Applier.HasMeshRenderer) misbehave for some object types:

- No ring appears when a ChargeShrine is selected.
- The ring around a chest is broken (wrong position or size).
- Large scenery such as the ruins in the Forest cannot be selected at all.

Start by logging, per failing object, its genId or placement id, whether the raycast or the nearest path picked it (or neither), its renderer types and bounds, its collider, and its transform origin versus bounds centre. Likely suspects: HasMeshRenderer excluding objects whose renderers are not on the root's descendants or are a different Renderer subclass, origins that are not at the base, bounds that include child effects, and ruins being tileObject genIds (not pickable) or beyond the half-tile nearest-object distance.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Each of the three failures is reproduced and its cause recorded in the task notes
- [x] #2 A selected ChargeShrine shows a ring beneath it
- [x] #3 A selected chest shows a ring that sits at its base and fits its footprint
- [x] #4 The Forest ruins can be selected (or the decision to leave them unpickable is recorded, with the reason)
- [x] #5 Logic that can be tested without the game has tests written first
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add temporary diagnostics: on select, log genId, renderer types, per-renderer bounds, collider types, transform origin vs bounds centre; in PickAt log which path (raycast/nearest/none) and the hit transform; log ruins' genId category and distance to cursor ground point.
2. Relaunch via the megabonk MCP (task mod:build, relaunch), select a ChargeShrine, a chest and the Forest ruins, and record each cause in the task notes (AC1).
3. Write failing tests first for any Unity-free logic the fixes need (ring centre/radius from bounds, pickability rules), in tests/MegabonkLevels.Tests/object_tool_tests.cs; confirm they fail.
4. Fix RefreshOutline / HasMeshRenderer / IsPickableGenId / nearest-object pick per the recorded causes; keep diagnostics only if cheap and useful, otherwise remove.
5. Re-verify the three cases in the running game with screenshots; update docs (docs/development.md or the editor doc) and run task check.
6. Conventional commit, no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
ChargeShrine reproduced (gen:object:ChargeShrine:0007, picked via raycast). Renderers: root MeshRenderer bounds centre y=0 extents (16.8, 12.5, 16.8); MinimapIcon MeshRenderer extents (10, 0, 10) at y=0; ShrineEnergy SkinnedMeshRenderer extents 0; AltarIcon MeshRenderer at y=9.17. Combined box.min.y is about -12.5, so RefreshOutline puts the ring 12.5 below the origin, under the terrain, and sizes it from the 16.8 extents. Cause: the combined bounds include the oversized root renderer and the MinimapIcon, which are not the visible model.

Shrine cause refined: the root MeshRenderer of ChargeShrine is DISABLED (material Forcefield_Shrine, the charge-radius sphere, extents 16.8/12.5/16.8). RefreshOutline/HasMeshRenderer count disabled renderers. The shrine's click also lands on its SphereCollider/Fader BoxCollider, so it raycast-picks fine; only the ring is wrong.

Chest reproduced (gen:object:Chest:0001, picked via nearest, not raycast). Visible mesh bounds are sane (extents 1.26/1.37/1.41, centre y 0.73), but a MinimapIcon MeshRenderer (extents 6/0/6 at y=0) is included, so the ring radius comes from 6, not 1.4. Same MinimapIcon is on the shrine. Fix for both: skip disabled renderers and MinimapIcon.

Ruins reproduced and cause found: the ruin pieces are scene roots named without the (Clone) suffix ('Castle', 'Castle (1)', 'CastleLying', 'Ruins (1)', 'Pillar', 'Pillar (1)', 'Cube', 'Crate (n)', 'Tree'), each a single MeshRenderer with a collider, placed by the tileObject generator. The tileObject:#### entries in the index are the bare 'Forest0_PrefabN(Clone)' placeholders: 0 children, 0 renderers, and not pickable. BuildIndex only collects '(Clone)' roots after TileObjectsParent, so these pieces are not in the index. Raycast hits their colliders but TargetOf finds no target, and the nearest fallback picks a nearby tree instead.

Ruins decision (Lance): leave unpickable, reason recorded in docs/development.md. Fix: ObjectTools.IsModelRenderer (test written first) used by HasMeshRenderer and RefreshOutline. Shrine ring verified in the running game. Chest ring: fix applied by the same renderer filter but not visually confirmed (the ring was too small to judge from the editor camera), so AC #3 stays unchecked.

Chest follow-up: after the renderer filter a chest at the player start still showed no ring. Causes: ring base used bounds min.y, which is below the ground for models partly buried (chest min.y -0.64, rock -8.48 relative to origin y 0), and the radius (0.4 x extent) put the ring inside the chest's own footprint. Fixed with ObjectTools.RingBaseY (clamp to the tile surface) and ObjectTools.RingRadius (small objects get a ring that clears the mesh), both tests first. Verified in the running game: red ring around the chest base and around a tree base.

REOPENED. The task was closed too early; later in-game use by Lance showed selection is still not right. Status after the follow-up commits (7b3652a ring base/radius, df56367 trigger-aware picking, plus the commit that closes this note):

What works (confirmed in the running game): shrine ring appears; chest ring visible around its base; clicking chest, tree trunk, rock and shrine from the default overview each selects that object via the raycast path.

Cause found for picking: Physics.Raycast hit TRIGGER colliders far larger than the models (shrine charge sphere 12.5, tree FadeCollider about 11x15, chest sphere 1.3), so they swallowed clicks. ObjectPicker.NearestHit now accepts a trigger only when the ray crosses the object's model renderer bounds, and a solid non-object collider (terrain) blocks what is behind it. Nearest-object fallback radius cut from half a tile to an eighth.

Test-harness trap: an injected mouse position (mouse tool) overrides the real cursor until cleared with mouse clear. My earlier testing left it set, which can make Lance's real clicks land at my last coordinates and was probably behind some of the reported imprecision. Clear it after every harness test.

STILL OPEN, reported by Lance and not resolved: (1) a boulder (rock_medium_01) selects per the log but no ring is visible; I changed the selection ring to ignore depth (render queue 4000, ZTest Always) and it still showed no ring on the boulder, cause unknown, I was about to log ring base y, radius and origin vs the tile surface (SurfaceYAt may return a different level than the rock origin). (2) The shrine ring/hit area still looks too small against its perceived size: its only model renderer is AltarIcon (extents 0.55/0.99/0.95) so the click target and ring come from that small bound; I raised the small-object ring scale to 2 (cap 3) but did not verify it. (3) Selecting objects close together is not confirmed precise; I could not reproduce a boulder-selects-chest result with injected clicks (5 clicks across both stones all picked the boulder). Lance suspects another asset layer interferes; not investigated beyond the trigger finding.

Last commit contains the on-top ring material and the larger small-object ring radius; neither is confirmed to fix the reported problems. Ruins decision (unpickable) stands.
<!-- SECTION:NOTES:END -->
