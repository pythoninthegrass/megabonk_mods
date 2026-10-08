---
id: TASK-008.01
title: Research putting the player position on the game's minimap
status: In Progress
assignee: []
created_date: '2026-10-08 05:14'
updated_date: '2026-10-08 06:07'
labels:
  - level-editor
dependencies: []
parent_task_id: TASK-008
priority: low
ordinal: 43000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Decide whether the game's own minimap can show the player's world position or grid cell, and what it would cost. This is research only; the dev-only on-screen readout is a separate sibling task and does not wait on this one. Megabonk is a Unity IL2CPP game modded through MelonLoader and Il2CppInterop. The IL2CPP dump at .tools/il2cpp_dump/dump.cs lists types, fields and RVAs but no method bodies, so findings need confirming in the running game through the dev harness (see docs/development.md). Record the result in docs/runtime-map-structure.md or a new docs/*.md file as facts about the game, not as task history.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The minimap's component types, the objects that draw it and its player/enemy markers are identified from the dump and confirmed in the running game
- [x] #2 The mapping between world coordinates and minimap coordinates is documented, or documented as not recoverable
- [ ] #3 A written verdict states whether adding a text label for position or cell on the minimap is viable, with an estimate of the added code and the risk of breaking on a game update
- [ ] #4 Findings are written into docs without citing task IDs
<!-- AC:END -->





## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
