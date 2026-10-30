---
id: TASK-025.04
title: 'Keep collision, grind and window behaviour attached to their pieces'
status: To Do
assignee: []
created_date: '2026-10-30T16:24:00Z'
updated_date: '2026-10-30T16:24:00Z'
labels:
  - level-editor
  - thps
dependencies:
  - TASK-025.03
references:
  - scripts/build_thps_level.py
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - src/MegabonkLevels.Mod/grind_gate_patch.cs
documentation:
  - docs/development.md
  - docs/thps-warehouse-pieces.md
modified_files:
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
  - docs/development.md
parent_task_id: TASK-025
type: feature
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Depends on TASK-025.03, which provides the placeable pieces. Grind behaviour in the Warehouse currently lives in hidden game rails laid along mesh edges by the generator, and the pass-through windows are an exception baked into the pack's collision mesh by world bounds. Both are tied to fixed positions, so once a piece moves on its own they would be left behind: a moved ramp would keep grinding where the old one was, and a relocated window would either stay solid or open a hole in whatever wall it moved into. The behaviour has to travel with the geometry it belongs to.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Moving, rotating, scaling or deleting a ramp or rail piece moves or removes its grind path with it, leaving no grindable edge behind
- [ ] #2 Duplicating a piece gives the copy its own collision and grind behaviour, independent of the original
- [ ] #3 Pass-through window behaviour belongs to the window piece, so a relocated window opens its own opening and does not punch one through unrelated geometry
- [ ] #4 Rail posts and other support geometry stay attached to the piece they support
- [ ] #5 Joined ramp modules hand off grinds cleanly across their seams
- [ ] #6 The shipped level's grind and collision behaviour is unchanged, confirmed by the preservation check from TASK-025.01
- [ ] #7 Tests cover the behaviour-attachment logic that can be exercised outside Unity, and docs record how a piece carries its collision and grind data
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
