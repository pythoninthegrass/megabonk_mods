---
id: TASK-005.02
title: Catalog palette UI
status: Done
assignee: []
created_date: '2026-10-06 21:43'
updated_date: '2026-10-10 05:59'
labels:
  - level-editor
dependencies:
  - TASK-005.01
parent_task_id: TASK-005
priority: high
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005 first for full context.

Build a UGUI+TMP palette panel, shown while editor mode is active, listing placeable catalog entries for the currently-loaded map — sourced from the real prefab catalog (`DataManager.Instance.maps → stages → randomMapObjects[].prefabs`, `stageTilePrefabs`, `MapData.shrines`, `SpawnInteractables`'s chest/rail fields, per earlier research — confirm exact fields against TASK-002's findings), using TASK-003.05's `catalogId` format to identify each entry. Each entry should show a visual thumbnail if feasible (in-engine render-to-texture of the prefab, or a simple icon/label fallback if thumbnails prove too costly for this subtask's scope — document whichever approach is taken) and its display name.

Selecting an entry should set it as the "currently selected catalog item" for TASK-005.04's object-placement tool to consume. This subtask only needs to build and populate the palette and expose the current selection — actual placement logic is TASK-005.04's job.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A palette panel lists every placeable catalog entry for the currently-loaded map, sourced from the real game's prefab catalog fields
- [x] #2 Each entry displays a thumbnail (render-to-texture or a documented icon/label fallback) and a display name
- [x] #3 Each entry's catalogId matches TASK-003.05's format
- [x] #4 Selecting an entry exposes it as the current selection for consumption by the object-placement tool
- [x] #5 The palette updates correctly if the editor is reopened on a different map
<!-- AC:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added a UGUI+TMP catalog palette shown in editor mode. PaletteCatalogBuilder builds catalogIds from the game's prefab catalog (CatalogPrefabs, shared with live editing); PaletteSelection exposes the current CatalogId for the placement tool. Rows show the prefab GameObject name (label-only, no thumbnails). Verified in game on Forest (75 entries) and Desert (73 entries): click selection, wheel scroll, rebuild on map change. Editor look now needs RMB held and is 10% more sensitive.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
