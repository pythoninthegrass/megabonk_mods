---
id: TASK-021.16
title: Let the player move through the windows at the top of the starting slope
status: To Do
assignee: []
created_date: '2026-10-28 05:25'
labels:
  - thps
  - level-editor
dependencies: []
documentation:
  - docs/thps-warehouse-layout.md
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
parent_task_id: TASK-021
priority: medium
ordinal: 104000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The windows at the top of the starting slope are solid, but a faithful half pipe stands behind them like the source material. Remove their collision so the player can move through them into that half pipe. TASK-021.09 opened the intact secret room windows by dropping collision faces selected by position in unity/pack-authoring/Assets/Editor/ThpsPack.cs (commit 38c2786), because the window material is shared with solid windows elsewhere; reuse that approach.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The player can move through the windows at the top of the starting slope into the half pipe behind them
- [ ] #2 Solid windows elsewhere in the warehouse keep their collision
- [ ] #3 Any new pack behaviour is covered by tests, and docs/thps-warehouse-layout.md is updated
- [ ] #4 A screenshot of the opened windows is saved under .tools/evidence/ and noted in the task
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
