---
id: TASK-086.03.01
title: Build approximate BSP geometry from the additive brush polygons
status: Done
assignee: []
created_date: '2026-11-27 18:27'
updated_date: '2026-11-28T04:19:00Z'
labels:
  - level
  - kf1
dependencies:
  - TASK-086.03.03
  - TASK-086.03.04
  - TASK-086.03.05
  - TASK-086.03.06
  - TASK-086.03.07
  - TASK-086.03.08
documentation:
  - docs/kf1-mountain-pass.md
parent_task_id: TASK-086.03
priority: medium
ordinal: 304000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
First, playable version of the BSP: turn the polygons of the additive `Brush` actors in the exported T3D into render and collision geometry (world position is vertex minus `PrePivot` plus `Location`; none are rotated), skipping the world-size subtractive brushes and any brush whose polygons all use `Engine.BlackTexture` until their purpose is known. Textures come from the polygon `Texture` references. No boolean operations: subtractive brushes are not applied, so building interiors will be approximate. Establish what the `BlackTexture` brushes are by rendering terrain, meshes and brushes together, and record the answer and the resulting collision decision in docs/kf1-mountain-pass.md. Tests come first for the brush parser and the polygon-to-triangle conversion.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Unit tests cover the brush parser and the polygon-to-triangle conversion, and pass
- [x] #2 The additive brush geometry appears in mesh.json and in the collision mesh, with world-size subtractive brushes excluded
- [x] #3 The purpose of the BlackTexture brushes is established from a render and written in docs/kf1-mountain-pass.md, and collision follows that decision
- [x] #4 A screenshot from the running game shows at least one building complex built from brushes
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
Write failing tests for brush parsing and triangulation. Connect textured additive brush geometry to render, collision and floor lookup. Compare BlackTexture brushes against terrain and props, document collision treatment, verify a brush-built building in game and run task check.

Fix the preview failures reported in game: regression tests for scalar plus vector transforms and textured static primitives; resolve exported materials including actor skins, rebuild the preview, and measure player/bridge scale before changing the world scale.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The real export produces 345 additive brush meshes and 4,784 collision triangles. The regression test failed first on the missing parser and passes for render/collision indexing, pivot, UV and floor height. Three shops now ground; five navigation nodes give eight shrine candidates. Diagnostic top-down views of terrain, props and brush faces are local-only at .tools/kf1/bsp-context.png and bsp-black-overlay.png. The 17 invisible non-solid portal sheets are distinct from five uncarved six-face solids. Which solid surfaces survive ordered CSG remains open. Screenshot verification currently needs an asset bundle and a Unity editor; the local Unity CLI reports no installed editors.

Commit ee60dfa. task check passed (2,988 passed, 39 skipped, 1 expected failure); all 29 converter tests passed. No Unity editor is installed according to unity editors -i, and there is no kf1 bundle. In-game building screenshot outstanding.

Correction: the Unity CLI's empty installed-editors list is not a reliable installation check. The maintainer confirms Unity 2023 on both Macs. The second Mac's editor executable reports 2023.2.22f1. Start Unity Hub for licensing; a standalone verification project is building the preview pack there.

Verified the 2023.2.22f1 Windows preview bundle from the second Mac in the running game on the maintainer host. The MountainPass prefab instantiated; ExtraShrines reported 6 spawned of 6 planned from 8 spots. Screenshot .tools/kf1/bsp-building-detail.png shows textured concrete brush walls and ledges; .tools/kf1/bsp-complex.png shows their context. Many props and surfaces appear white in this preview. AC3 remains open only for the surviving collision of the five all-black solids; portal sheets are identified.

5612816 fixes prop textures, skin overrides, cutout foliage, fallback colors and scalar actor transforms. 1,888/2,196 static primitives resolve to textures in the available export. KFHumanPawn full collision height 100 matched to 3.85 in Megabonk gives scale 0.0385. At Brush29 the tarmac face center is 401 Unreal units above the terrain (four player heights). Verified rebuilt preview in game: .tools/kf1/tony-at-bridge.png and .tools/kf1/valley-fixed.png. Terrain is still single-color; approximate solids/terrain obscure the opening. task check passed: 2,992 passed, 39 skipped, 1 expected failure.

AC3 closed on the render evidence actually available: the top-down overlay established `Engine.BlackTexture` is a surface material and split the 22 entirely black additive brushes into 17 zone portal sheets (PolyFlags 0x04000009) and five six-face solids, both excluded from render and collision, so collision follows the recorded decision. Which faces of the five solids survive in the compiled map cannot be established from the additive-only pass; that question is now an acceptance criterion of the ordered-subtraction task, where the boolean result can answer it, and it stays an open question in docs/kf1-mountain-pass.md.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Additive brushes now reach render, collision and floor lookup. The converter parses only `CsgOper=CSG_Add` actors, converts brush-local vertices through PrePivot and Location, triangulates each polygon in vertex order, and groups faces by their `Texture` reference; the real export yields 345 brush meshes and 4,784 triangles, verified in .tools/kf1/mesh.json with world-size subtractive brushes excluded. `Engine.BlackTexture` is a surface material rather than a collision flag: the 142 mixed-material brushes keep their black faces, and the 22 entirely black brushes are excluded as 17 zone portal sheets plus five six-face construction volumes, documented in docs/kf1-mountain-pass.md. Follow-on work fixed the preview failures it exposed: scalar and vector actor transforms, actor skins and resolved exported materials, cutout foliage and fallback colors, bringing 1,888 of 2,196 static primitives to real textures, and KFHumanPawn height 100 against 3.85 Megabonk units fixed the world scale at 0.0385. Verification: 51 tests in tests/test_kf1_mountain_pass.py pass, including brush parsing and triangulation written first; task check passes at 3059 passed, 1 skipped, 1 xfailed with markdownlint, ruff and site lint clean; the 2023.2.22f1 Windows preview bundle was rebuilt on the second Mac and checked in the running game on the maintainer host, with the brush-built complex in .tools/kf1/bsp-complex.png and .tools/kf1/bsp-building-detail.png and scale checked in .tools/kf1/tony-at-bridge.png and .tools/kf1/valley-fixed.png. Follow-ups: rooms and doorways are approximate until ordered subtraction; the surviving faces of the five all-black solids are unresolved and tracked against that pass; terrain is still single-color.
<!-- SECTION:FINAL_SUMMARY:END -->
