---
id: TASK-060
title: >-
  Make the rail next to the totem at (162, 2, 65) grindable like the one at (27,
  2, 27)
status: In Progress
assignee: []
created_date: '2026-11-09T19:52:00Z'
updated_date: '2026-11-09T20:37:00Z'
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
- [x] #1 The rail next to the totem near (162, 2, 65) starts and sustains a grind with the slide button, matching the behavior of the rail at (27, 2, 27), verified in the running game.
- [x] #2 The rail at (27, 2, 27) still grinds as before.
- [x] #3 The change is covered by a test written first where the logic is testable, and any authored level or piece data is regenerated.
- [ ] #4 The change ships as a minor version bump through release-please, and the resulting GitHub release is built, validated and submitted to Thunderstore by the automated workflow without a manual upload.
- [ ] #5 The published version appears on the Thunderstore package page with the runtime-only contents and the BepInEx dependency intact.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Diagnosis (checked in the running game and level data): (27,2,27) stands on Shorty's ledge, whose top edge has hidden game rails (LEDGE_LIPS in scripts/build_thps_level.py). (162,2,65) stands on the matching raised block beside the totem. Its top edge exists in the mesh (ws.ledge_runs finds the chain (170.75,3.79,46.76)->(170.75,51.69)->(162.57,60.14)->(162.57,68.59)->(168.76,75.94)->(168.76,79.77)->(173.09,79.77)) but no rail is laid on it; the nearest rail is 14 units away. So the fix is missing rails, not a broken one.

Plan:
1. Tests first (tests/test_build_thps_level.py, tests/test_thps_attachments.py): an EAST_LEDGE_LIPS tuple joins end to end with gentle turns, is a subset of COPING_LIPS, its corners are corners of the mesh ledge runs, and the rail at (162.57,3.79,64) exists. Confirm they fail.
2. Add EAST_LEDGE_LIPS to scripts/build_thps_level.py and COPING_LIPS; extend COPING_OWNERS and the attachment path count in scripts/build_thps_attachments.py so the piece pack carries the new grind paths.
3. Regenerate levels/thps.mblevel.json, attachments.json and the pack (task thps:pack --force); refresh the preservation baseline deliberately.
4. Verify in the game: slide held, grind starts and sustains on the east ledge; west ledge still grinds.
5. Update docs (thps-warehouse-layout.md coping section and counts, thps-warehouse-pieces.md path table); task check.
6. Release (AC #4/#5) goes through release-please and the TASK-056.06 workflow; it is blocked on that task and will be handled after the fix, with Lance's go-ahead.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Cause: the east deck ledge edge had no rails; EAST_LEDGE_LIPS (5 segments, owner piece-ledge-east) added in scripts/build_thps_level.py after the start lip so path indices 0-27 are unchanged. Regenerated levels/thps.mblevel.json (48 -> 53 edits), attachments.json (58 -> 63 attachments) and the preservation baseline (deliberate refresh). Tests written first (4 new in tests/test_build_thps_level.py); task check passes (1369 Python tests, C# suite).

In-game evidence (relaunch on regenerated level, slide held via grind_slide): east ledge 'GrindGate: slide held, grind started at (162.6, 7.7, 63.0) on the rail at (162.6, 3.7, 64.4)', then RailHandoff moved the grind onto the rail at (170.8, 3.8, 49.2) (sustained across the chain). West ledge: 'grind started at (25.8, 7.8, 38.0) on the rail at (25.8, 3.6, 37.5)' with sparks in the screenshot. Slide released at (162.6, 5.7, 66.0): 'grind start blocked ... by the StartRail hook', same as the west.

Not done: the Unity pack bundle was not rebuilt (task thps:pack --force) so the piece-assembled editable level has not been checked in game; the chain stops at (168.76, 3.79, 79.77) because the next mesh edge turns 90 degrees. Release (AC #4, #5) is pending: a fix: commit gives a patch bump, so the minor bump needs a feat: type or release-as, and the pipeline from TASK-056.06 is still In Progress.
<!-- SECTION:NOTES:END -->
