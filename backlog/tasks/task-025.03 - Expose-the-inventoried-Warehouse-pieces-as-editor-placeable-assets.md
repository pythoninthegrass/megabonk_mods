---
id: TASK-025.03
title: Expose the inventoried Warehouse pieces as editor-placeable assets
status: To Do
assignee: []
created_date: '2026-10-30T16:24:00Z'
updated_date: '2026-10-30T16:24:00Z'
labels:
  - level-editor
  - thps
dependencies:
  - TASK-025.02
references:
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - unity/pack-authoring/packs/thps/manifest.json
  - src/MegabonkLevels.Mod/pack_palette_entries.cs
documentation:
  - docs/asset-bundles.md
  - docs/thps-warehouse-pieces.md
  - docs/thps-warehouse.md
parent_task_id: TASK-025
type: feature
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Depends on TASK-025.02, which supplies the piece inventory naming what each asset is and which faces it owns. Today the pack builds one merged mesh and one collision mesh, so the editor sees a single object; making the arena rebuildable requires each piece to exist as its own asset in the thps pack and appear in the editor's palette. Ramp modules additionally need shared pivots and mating edges, otherwise authors cannot join sections into a continuous surface and the kit is only a disassembly.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every piece from the inventory exists as its own asset in the thps pack and appears in the editor's pack palette with a recognisable name
- [ ] #2 Each piece keeps its original textures, its own collision, and a sensible local pivot
- [ ] #3 Ramp modules share pivot conventions and mating edges so sections placed end to end form a continuous riding surface without seams or steps
- [ ] #4 A piece can be selected, moved, rotated, scaled, duplicated and deleted with the existing object tools
- [ ] #5 The original single Warehouse asset and its collision mesh are still built, still listed, and still loadable so the shipped level is unaffected
- [ ] #6 Tests cover the piece-building logic that can be exercised outside Unity, and docs describe the palette and the module set
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
