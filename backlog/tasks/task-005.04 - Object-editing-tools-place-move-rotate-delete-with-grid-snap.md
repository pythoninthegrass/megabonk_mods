---
id: TASK-005.04
title: 'Object editing tools (place, move, rotate, delete) with grid snap'
status: To Do
assignee: []
created_date: '2026-10-06 21:43'
labels:
  - level-editor
dependencies:
  - TASK-005.02
parent_task_id: TASK-005
priority: high
type: feature
ordinal: 26000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005 first for full context.

Implement object placement/manipulation tools: place the currently-selected palette item (from TASK-005.02) at the cursor's world position with grid snapping, move an existing placed/generated object (by clicking and dragging, or click-to-select then click-to-reposition), rotate it, and delete it. Each action constructs the corresponding TASK-003.02 op (`PlaceObject`, `MoveObject`, `RemoveObject`) with the correct `catalogId`/`genId`/placement-id target, pushes it through the `EditStack`, and applies it live via TASK-004.02's logic.

Grid snapping should align to the tile grid spacing from `StageData.mapParameters` (same source TASK-004.02 uses — do not hardcode a separate snap value).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The currently-selected palette item can be placed at the cursor's world position with grid snapping aligned to StageData.mapParameters's tile spacing
- [ ] #2 An existing object (generator-spawned or editor-placed) can be selected, moved, and rotated
- [ ] #3 An existing object can be deleted
- [ ] #4 Each action constructs the correct TASK-003.02 op with correct target reference (catalogId for new placements, genId or placement-id for existing objects) and applies it through EditStack + TASK-004.02's live-application logic
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
