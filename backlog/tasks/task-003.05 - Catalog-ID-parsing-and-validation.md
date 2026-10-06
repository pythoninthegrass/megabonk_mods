---
id: TASK-003.05
title: Catalog ID parsing and validation
status: To Do
assignee: []
created_date: '2026-10-06 21:41'
labels:
  - level-editor
dependencies:
  - TASK-003.01
parent_task_id: TASK-003
priority: medium
type: feature
ordinal: 15000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-003 first for full context.

Define and implement the `catalogId` format used by `PlaceObject` edits (TASK-003.02) to reference placeable prefabs, plus parsing/validation:

- Game-asset namespace: stable string keys identifying existing game prefabs, e.g. `forest/stage0/randomMapObjects/2/Tree_03` or `interactable/chest` — the exact structure should be driven by however TASK-002's findings describe the game's prefab catalog being organized (`DataManager.Instance.maps → stages → randomMapObjects[].prefabs`, `stageTilePrefabs`, `MapData.shrines`, `SpawnInteractables`'s chest/rail fields) — read TASK-002's docs before finalizing the exact segments.
- Reserved future namespace: `bundle:<pack>/<asset>` for TASK-007's custom asset packs. Nothing produces these IDs yet, but parsing/validation must accept the format now so TASK-007 doesn't need to revisit this task's validation logic later.
- A parser that splits a raw string into a typed representation (namespace + segments) and a validator that rejects malformed IDs (empty segments, invalid characters, unknown namespace prefix, etc. — define the exact character/segment rules and document them).

TDD: write tests for valid game-asset IDs, valid reserved `bundle:` IDs, and a table of malformed inputs (empty string, missing namespace, invalid characters, trailing/leading separators) each expected to fail validation with a clear reason.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The catalogId format is defined and documented in docs/level-format.md, covering both the game-asset namespace and the reserved bundle: namespace
- [ ] #2 A parser converts a raw catalogId string into a typed representation distinguishing namespace and segments
- [ ] #3 A validator accepts well-formed game-asset and bundle: IDs and rejects a documented set of malformed inputs, each with a clear validation failure reason
- [ ] #4 Unit tests cover valid IDs in both namespaces and a table-driven set of malformed inputs
- [ ] #5 The game-asset ID structure is cross-checked against TASK-002's documented prefab catalog organization rather than invented independently
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
