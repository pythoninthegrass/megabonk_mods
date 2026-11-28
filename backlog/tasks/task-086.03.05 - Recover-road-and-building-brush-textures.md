---
id: TASK-086.03.05
title: Recover road and building brush textures
status: To Do
assignee: []
created_date: '2026-11-27 21:46'
updated_date: '2026-11-28T06:28:00Z'
labels:
  - kf1
  - level
dependencies:
  - TASK-086.02
references:
  - scripts/kf1_mountain_pass.py
  - tests/test_kf1_mountain_pass.py
documentation:
  - docs/kf1-mountain-pass.md
  - docs/asset-bundles.md
parent_task_id: TASK-086.03
priority: medium
ordinal: 308000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Start from brush_material and append_brushes. Resolve the seven outstanding surfaces: Architecture_T.Rooftops.concreteroof, Architecture_T2.Plaster.Stucco_1480_colored, KillingFloorLabTextures.LabCommon.Door_Inset, KillingFloorTextures.LondonCommon.{ConcreteFloor,LondonStreetTarmac,PaintFleckedWindow}, Landscape_T.Soil.earth_1051. Use original packages and material chains. Engine.BlackTexture has separate BSP semantics; preserve the existing geometry and collision decision.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each of the seven references maps to its original surface or an evidenced intentional non-rendering material; record package/object chains in the map notes.
- [ ] #2 Tests cover a non-square texture, nonzero polygon origin and two faces sharing a texture; UV repeat and orientation remain correct.
- [ ] #3 Verify road, concrete and facade against matched KF1 views; painted lines alone are not evidence of textured asphalt. Brush and collision geometry remain unchanged.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Findings 2026-11-28 from TASK-086.03.02: brush textures named Package.Group.Name are now read from out/<Package>/<Group>/<Name>.tga (umodel -groups layout) before out/<Package>/Texture/. ConcreteFloor, LondonStreetTarmac, PaintFleckedWindow, Door_Inset and earth_1051 were exported on the KF1 box into .tools/kf1/out. Still unresolved: Architecture_T.Rooftops.concreteroof (557 faces) and Architecture_T2.Plaster.Stucco_1480_colored (117), because no Architecture_T*.utx exists under the KF1 box's game files or Steam library; SheetMetal_combiner (7) is not in KillingFloorManorTextures. Engine.BlackTexture (393 faces) renders black on purpose and is unchecked against KF1. Hand-picked fallback and terrain colors are now stored linear (the vertex tint shader writes vertex colors unconverted).
<!-- SECTION:NOTES:END -->
