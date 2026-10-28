---
id: TASK-021.09
title: Import the extracted Warehouse mesh and shell into the thps pack
status: To Do
assignee: []
created_date: '2026-10-28 02:41'
updated_date: '2026-10-28 02:41'
labels:
  - thps
  - level-editor
dependencies:
  - TASK-021.08
documentation:
  - docs/thps-warehouse-layout.md
  - docs/asset-bundles.md
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
parent_task_id: TASK-021
priority: high
ordinal: 97000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Replace the hand-built flat-coloured ramps and the Forest cliff-ring look with the extracted Warehouse mesh: floor slab, ramps, decks, walls, windows, doors and trusses, with PS1-style point-filtered textures. The thps pack (unity/pack-authoring/Assets/Editor/ThpsPack.cs) gets a Warehouse prefab with a visual renderer and a MeshCollider on the ground layer, scaled uniformly so the 1.8 m skater is about 4.4 units tall (the approved 4.4 units per metre). The old QuarterPipe, Kicker, Block, Taxi and Corridor prefabs and the STRUCTURES table in scripts/build_thps_level.py stay until the new mesh is verified in game. Depends on the extraction task for the OBJ and textures.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The thps pack contains a Warehouse prefab built from the extracted mesh with a ground-layer MeshCollider, and the pack version is bumped
- [ ] #2 The level places the Warehouse at one uniform scale and the room fits the arena, enlarging INNER_X and INNER_Z if needed
- [ ] #3 The tile floor and cliff ring no longer show inside the room, and the kill floor still ends a fall
- [ ] #4 In-game screenshots from the south-east at pitch 45 and from ground level are compared with tools/thps_warehouse_items_map.png and frames 4, 12 and 138, and differences are listed
- [ ] #5 Textures are point-filtered with no mipmaps and read as the PS1 original
- [ ] #6 The old hand-built structures are removed only after the above is verified, and docs/thps-warehouse-layout.md is updated to describe the new structure instead of the retired tables
- [ ] #7 The player spawns inside the shell, can move, and enemies spawn and move inside it
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
