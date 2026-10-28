---
id: TASK-021.16
title: Let the player move through the windows at the top of the starting slope
status: In Progress
assignee: []
created_date: '2026-10-28 05:25'
updated_date: '2026-10-28 06:24'
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
- [x] #2 Solid windows elsewhere in the warehouse keep their collision
- [x] #3 Any new pack behaviour is covered by tests, and docs/thps-warehouse-layout.md is updated
- [ ] #4 A screenshot of the opened windows is saved under .tools/evidence/ and noted in the task
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Branch fix/task-021.16-start-windows (commit 9e28cb1). The two start-slope windows are the F2184063 panes at world z -73.3, x 81-106 and 114-139, y 27.8-37.2; the pack drops collision faces inside StartSlopeWindowBounds (x 80-140, y 27-38, z -75 to -72), generalised with the secret room into OpenedWindowBounds. Other F2184063 windows keep collision (position-only filter). Pack 2.0.9, level regenerated, docs/thps-warehouse-layout.md updated, tests added.

NOT yet verified by hand (AC 1, 4): the harness cannot drive the game's own movement input (key/mouse injection reaches only editor code), so walking through the windows was not tested. Evidence so far: .tools/evidence/task-021.16-start-windows-before-walk.png shows the player at the start facing the windows. Lance: walk through both panes into the half pipe, and note a screenshot here.

Branch fix/task-021.16-start-windows is the base of the train: 021.14 docs, 021.19 and 021.15 are stacked on it in that order.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
