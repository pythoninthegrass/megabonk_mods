---
id: TASK-021.20
title: Remove the dark background behind the ceiling chain hooks
status: To Do
assignee: []
created_date: '2026-10-28T21:02:00Z'
labels:
  - thps
  - level-editor
dependencies: []
documentation:
  - docs/thps-warehouse-layout.md
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
parent_task_id: TASK-021
priority: medium
type: bug
ordinal: 110000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The hanging ceiling chains near world (156, 28, 27) render on an opaque dark blue-grey quad, so the warehouse behind them is hidden and only the chain links should show. Before screenshot: /Users/lance/Desktop/Screenshot 2026-10-28 at 3.59.52 PM.png (copy it to .tools/evidence/ as the before shot).

Context for a fresh implementer: the chain texture comes from skware_l.psx, where magenta is the transparency key (see TASK-021.08 notes). Likely causes are the key or alpha being lost during extraction, or the material using an opaque shader. Mesh and material import is in unity/pack-authoring/Assets/Editor/ThpsPack.cs; shader remap is from TASK-007.03.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The cause of the opaque background is identified and noted in the task
- [ ] #2 The chains show only their links, with the scene visible through the gaps, confirmed by before and after screenshots saved under .tools/evidence/
- [ ] #3 Other textures using the same transparency key are checked for the same fault
- [ ] #4 Any new generator or pack behaviour is covered by tests written first, and docs/thps-warehouse-layout.md is updated
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
