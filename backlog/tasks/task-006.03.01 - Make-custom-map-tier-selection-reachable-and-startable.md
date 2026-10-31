---
id: TASK-006.03.01
title: Make custom-map tier selection reachable and startable
status: To Do
assignee: []
created_date: '2026-10-31T17:10:00Z'
labels:
  - level-editor
dependencies: []
references:
  - src/MegabonkLevels.Mod/map_selection_patch.cs
  - src/MegabonkLevels.Mod/level_loader_patch.cs
documentation:
  - docs/development.md
parent_task_id: TASK-006.03
priority: high
type: bug
ordinal: 130000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Live Proton verification on wm2 (CachyOS, Proton Experimental, Megabonk 1.0.69, MelonLoader 0.7.3) proves MegabonkLevels initializes and lists Warehouse after installing thps.mblevel.json and its Windows pack. Selecting Warehouse leaves Tier 1 unselectable while the cursor highlights a blank Tier 3 option; the user cannot confirm and start the custom level. Latest.log records selection of thps.mblevel.json but no subsequent start. This is a player-facing launch blocker, not a missing asset pack or a failure to load the mod. Preserve native-map tier behavior and do not require save resets or developer-only load commands.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Warehouse can be selected and started through the normal Map Selection flow on wm2 with mouse and controller navigation.
- [ ] #2 Custom-map selection never leaves focus on a hidden or blank tier option; its available tier is selectable and Confirm works.
- [ ] #3 Switching between custom and native maps restores native tier availability and navigation without stale selection state.
- [ ] #4 Regression coverage and a documented live wm2 verification include switching from a higher native tier to Warehouse and confirming that its level loads.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
