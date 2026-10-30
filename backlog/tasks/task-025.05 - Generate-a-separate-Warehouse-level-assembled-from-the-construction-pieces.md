---
id: TASK-025.05
title: Generate a separate Warehouse level assembled from the construction pieces
status: To Do
assignee: []
created_date: '2026-10-30T16:24:00Z'
updated_date: '2026-10-30T16:24:00Z'
labels:
  - level-editor
  - thps
dependencies:
  - TASK-025.01
  - TASK-025.03
  - TASK-025.04
references:
  - scripts/build_thps_level.py
  - levels/thps.mblevel.json
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
documentation:
  - docs/thps-warehouse.md
  - docs/thps-warehouse-layout.md
  - docs/level-format.md
  - docs/asset-bundles.md
parent_task_id: TASK-025
type: feature
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Depends on TASK-025.03 for the pieces and TASK-025.04 for their behaviour. The value of the kit is only realised when the Warehouse itself is expressed as an assembly of those pieces rather than one injected asset: that proves the set is complete, gives authors a working reference layout to take apart, and lets the same geometry be reused in new levels. It must be a second level file — the shipped levels/thps.mblevel.json and the assets it loads stay exactly as they are, which is what the preservation check exists to enforce.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A new level file reproduces the Warehouse layout from the individual pieces rather than one injected Warehouse asset
- [ ] #2 Its appearance and gameplay match the shipped level, confirmed by side-by-side screenshots through the megabonk MCP harness
- [ ] #3 Script-authored markers and settings that affect the arena — player and boss spawn placement, the boss portal, the radio, collectible placement, kill floor height and grind settings — are editable rather than fixed by the generator
- [ ] #4 The shipped levels/thps.mblevel.json and the pack assets it loads are untouched, confirmed by the preservation check from TASK-025.01
- [ ] #5 Pack versioning records the added assets so a level saved against the new kit reports a mismatch against an older pack
- [ ] #6 Tests cover the generator's new piece-assembly logic, and docs describe how to regenerate the editable level and how it relates to the shipped one
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
