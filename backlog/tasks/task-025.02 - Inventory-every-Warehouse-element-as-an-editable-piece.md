---
id: TASK-025.02
title: Inventory every Warehouse element as an editable piece
status: To Do
assignee: []
created_date: '2026-10-30T16:24:00Z'
updated_date: '2026-10-30T16:24:00Z'
labels:
  - level-editor
  - thps
dependencies:
  - TASK-025.01
references:
  - .tools/thps1/warehouse/warehouse.obj
  - scripts/build_thps_level.py
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
documentation:
  - docs/thps-warehouse.md
  - docs/thps-warehouse-layout.md
modified_files:
  - docs/thps-warehouse-pieces.md
parent_task_id: TASK-025
type: task
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The extracted OBJ carries roughly 252 object groups, but the pack importer discards those boundaries and merges faces by material, so the shipped mesh has no notion of a piece at all. Before anything can be exposed in the editor, someone has to decide what the pieces are: which groups form the taxi, which faces are the glass box walls and individual windows, where each half pipe and quarter pipe section begins and ends, and which script-injected elements need an editable form. Without that inventory, decomposition would be improvised per asset and would leave geometry stranded in an uneditable remainder.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Every face of the extracted mesh belongs to exactly one named piece, with no geometry left unassigned
- [ ] #2 Each inventory entry names the element in play terms (taxi, glass box wall, individual window, half pipe section, quarter pipe run, deck, ledge, rail, rail post, sign, floor, roof) and records the source OBJ groups or faces behind it
- [ ] #3 Script-injected elements — roof, floor patches, rail posts, hidden grind rails, boss portal and its spawn redirect, radio, collectibles, spawn markers and authored level settings — each appear with how they become editable
- [ ] #4 Ramp geometry is broken into composable module types, each with its profile, height and how it mates with neighbours
- [ ] #5 The inventory is written to a doc under docs/ and checked against the landmarks and structures recorded in docs/thps-warehouse.md
- [ ] #6 Docs link the inventory from the existing Warehouse documentation
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
