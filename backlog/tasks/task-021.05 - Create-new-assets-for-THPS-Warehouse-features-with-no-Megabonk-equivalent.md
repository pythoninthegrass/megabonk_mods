---
id: TASK-021.05
title: Create new assets for THPS Warehouse features with no Megabonk equivalent
status: To Do
assignee: []
created_date: '2026-10-27T22:08:00Z'
labels:
  - level-editor
  - thps
  - assets
dependencies:
  - TASK-021.03
  - TASK-021.04
documentation:
  - docs/asset-bundles.md
parent_task_id: TASK-021
priority: low
type: feature
ordinal: 91000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Some warehouse features, such as quarter pipes, the half pipe or the taxi funbox, may have no close Megabonk prop. The layout spec from TASK-021.03 lists which ones. This task builds those as custom assets through the asset pack pipeline from TASK-007 (see `docs/asset-bundles.md`) and places them in the level from TASK-021.04, replacing any placeholders.

If the spec finds that existing assets cover everything acceptably, close this task with a note saying so rather than inventing work.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Each feature the spec marks as needing a new asset exists as an asset in a pack that the mod loads
- [ ] #2 Each new asset renders correctly in game, checked with a screenshot
- [ ] #3 The assets are placed in the level at the specified positions and replace any placeholders
- [ ] #4 The player can ride or walk on the new assets without clipping or falling through
- [ ] #5 The authoring steps for the new assets are documented
- [ ] #6 If no new assets were needed, the task is closed with a note giving the reason
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
