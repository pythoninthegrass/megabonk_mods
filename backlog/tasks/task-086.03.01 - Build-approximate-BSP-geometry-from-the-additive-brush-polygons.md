---
id: TASK-086.03.01
title: Build approximate BSP geometry from the additive brush polygons
status: To Do
assignee: []
created_date: '2026-11-27 18:27'
labels:
  - level
  - kf1
dependencies: []
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
- [ ] #1 Unit tests cover the brush parser and the polygon-to-triangle conversion, and pass
- [ ] #2 The additive brush geometry appears in mesh.json and in the collision mesh, with world-size subtractive brushes excluded
- [ ] #3 The purpose of the BlackTexture brushes is established from a render and written in docs/kf1-mountain-pass.md, and collision follows that decision
- [ ] #4 A screenshot from the running game shows at least one building complex built from brushes
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
