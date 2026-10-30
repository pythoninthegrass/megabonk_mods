---
id: TASK-025
title: Make the THPS Warehouse editable from composable construction pieces
status: To Do
assignee: []
created_date: '2026-10-30T16:23:00Z'
labels:
  - level-editor
  - thps
dependencies: []
references:
  - scripts/build_thps_level.py
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - levels/thps.mblevel.json
  - scripts/thps_item_overrides.json
documentation:
  - docs/thps-warehouse.md
  - docs/thps-warehouse-layout.md
  - docs/asset-bundles.md
  - docs/development.md
modified_files:
  - scripts/build_thps_level.py
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - docs/development.md
priority: medium
type: feature
ordinal: 126000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Warehouse ships as one injected asset: scripts/build_thps_level.py places a single bundle:thps/Warehouse prefab, and unity/pack-authoring/Assets/Editor/ThpsPack.cs merges the extracted OBJ's ~252 object groups into material-keyed submeshes of one mesh. Nothing inside it — the taxi, the hanging glass box, its windows, the half pipes, the wall quarter pipes, the rails and ledges — can be selected, moved, duplicated or removed in the map editor, so a level author cannot manipulate or rebuild the arena, and none of its ramp vocabulary can be reused for a new layout.

The goal is a Warehouse construction kit: every element the generator injects becomes an individually editable piece, ramps additionally decomposed into composable modules (straight transitions, flat bottoms and decks, corners and end sections) with consistent pivots and mating edges so they join cleanly, and an editable level assembled from those pieces.

Hard constraint: the existing Warehouse level stays exactly as it is today. The editable kit is additive — new pack assets and a separate level — and the shipped level file and the assets it depends on are not regenerated, replaced or migrated.

Related work: TASK-021 built the current level from a single mesh; this initiative is the editor-editability follow-up, tracked separately because it changes how the pack, the generator and the editor tooling interact.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The map editor can select, move, rotate, scale, duplicate and delete every element the Warehouse generator injects, including the taxi, the hanging glass box, individual windows, the half pipes, the wall quarter pipes, the rails and the ledges
- [ ] #2 Ramps are additionally available as composable modules that join into continuous riding surfaces without seams
- [ ] #3 A separate level file reproduces the Warehouse layout from those pieces, matching the current level's appearance and gameplay
- [ ] #4 The existing levels/thps.mblevel.json and the pack assets it loads are unchanged, verified by an automated preservation check
- [ ] #5 All subtasks are done
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
