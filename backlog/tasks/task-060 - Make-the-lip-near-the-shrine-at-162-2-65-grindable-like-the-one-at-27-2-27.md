---
id: TASK-060
title: >-
  Make the rail next to the totem at (162, 2, 65) grindable like the one at (27,
  2, 27)
status: To Do
assignee: []
created_date: '2026-11-09T19:52:00Z'
updated_date: '2026-11-09T19:54:00Z'
labels: []
dependencies:
  - TASK-056.06
references:
  - >-
    backlog/tasks/task-056.06 -
    Automate-path-filtered-Thunderstore-package-builds-and-releases.md
  - 'https://thunderstore.io/c/megabonk/p/pythoninthegrass/Megabonk_Level_Editor/'
documentation:
  - docs/thunderstore.md
priority: medium
type: bug
ordinal: 211000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The Warehouse has a rail at (27, 2, 27) that the player can grind, but the matching rail on the opposite side of the level, next to the totem at (162, 2, 65), cannot be grinded. The two should behave the same. The fix ships as a minor version bump of the Thunderstore package and doubles as the first real release through the automated build and publish flow from TASK-056.06, so it must go out through that pipeline rather than a manual upload.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The rail next to the totem near (162, 2, 65) starts and sustains a grind with the slide button, matching the behavior of the rail at (27, 2, 27), verified in the running game.
- [ ] #2 The rail at (27, 2, 27) still grinds as before.
- [ ] #3 The change is covered by a test written first where the logic is testable, and any authored level or piece data is regenerated.
- [ ] #4 The change ships as a minor version bump through release-please, and the resulting GitHub release is built, validated and submitted to Thunderstore by the automated workflow without a manual upload.
- [ ] #5 The published version appears on the Thunderstore package page with the runtime-only contents and the BepInEx dependency intact.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
