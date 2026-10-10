---
id: TASK-005.04.01
title: 'Debug object selection rings and picking for shrines, chests and ruins'
status: To Do
assignee: []
created_date: '2026-10-10 08:11'
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
- [ ] #1 Each of the three failures is reproduced and its cause recorded in the task notes
- [ ] #2 A selected ChargeShrine shows a ring beneath it
- [ ] #3 A selected chest shows a ring that sits at its base and fits its footprint
- [ ] #4 The Forest ruins can be selected (or the decision to leave them unpickable is recorded, with the reason)
- [ ] #5 Logic that can be tested without the game has tests written first
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
