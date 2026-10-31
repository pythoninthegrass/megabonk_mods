---
id: TASK-025
title: Make the THPS Warehouse editable from composable construction pieces
status: Done
assignee: []
created_date: '2026-10-30T16:23:00Z'
updated_date: '2026-10-31T17:26:00Z'
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
- [x] #1 The map editor can select, move, rotate, scale, duplicate and delete every element the Warehouse generator injects, including the taxi, the hanging glass box, individual windows, the half pipes, the wall quarter pipes, the rails and the ledges
- [x] #2 Ramps are additionally available as composable modules that join into continuous riding surfaces without seams
- [x] #3 A separate level file reproduces the Warehouse layout from those pieces, matching the current level's appearance and gameplay
- [x] #4 The existing levels/thps.mblevel.json and the pack assets it loads are unchanged, verified by an automated preservation check
- [x] #5 All subtasks are done
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The Warehouse now ships as a construction kit alongside the untouched monolithic level. Every element the generator injects is an individually editable piece, exposed as pack-placeable assets; ramp modules carry collision, grind and window behaviour with them; levels/thps-editable.mblevel.json rebuilds the arena from 1444 kit edits with the taxi, benches, bins and cars placed individually; roof and glass modules are consolidated into reusable assets.

Ramps join into continuous surfaces: the main-pipe strip was rebuilt from two kit copies plus a flat bottom at the 19.722656 pitch, and both a ride (slides over the strip seam and the toe/flat joint without dropping through) and a grind (RailHandoff moves onto the rail across the coping joint and grinds continuously) ran through the joint on the generated level.

levels/thps.mblevel.json and the thps pack are byte-for-byte preserved, enforced by the thps-pack-preserving guard; the shipped level was relaunched clean with the radio clip and kill floor verified, and the authored grind and ride checked there as well.

Authoring is documented in docs/thps-warehouse-layout.md ("Authoring with the construction kit"): palette workflow, pivot-at-toe mating convention, the ramp assembly recipe, and the placement-height trap. task check is green (849 tests, markdownlint, ruff).
<!-- SECTION:FINAL_SUMMARY:END -->
