---
id: TASK-060
title: >-
  Make the rail next to the totem at (162, 2, 65) grindable like the one at (27,
  2, 27)
status: Done
assignee: []
created_date: '2026-11-09T19:52:00Z'
updated_date: '2026-11-14 21:55'
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
- [x] #4 The change ships as a minor version bump through release-please, and the resulting GitHub release is built, validated and submitted to Thunderstore by the automated workflow without a manual upload.
- [x] #5 The published version appears on the Thunderstore package page with the runtime-only contents and the BepInEx dependency intact.
<!-- AC:END -->

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

Pack: with Unity Hub running (open -a 'Unity Hub'), task thps:pack --force built both bundles (log: 'built StandaloneWindows64' and 'built StandaloneLinux64'); the bundle files were byte-for-byte unchanged by timestamp since the new rails are attachments, which pack:install copies from attachments.json. Ran task pack:install and task thps:editable-level, relaunched on levels/thps-editable.mblevel.json (251 edits): slide held, 'grind started at (162.6, 7.7, 63.0) on the rail at (162.6, 3.7, 64.4)', so the piece-assembled Warehouse grinds on the east ledge too. Docs: east ledge check added to docs/thps-warehouse-layout.md; site synced, npm run check and build pass; npm run test:site has one failure that predates this change (tests/site.test.js:37 expects scripts/mcp_server.py on the showcase page, the server now lives in src/megabonk_harness).

Release verification 2026-11-14 (AC #4, no manual upload): the fix commit 33ff224 is `feat(thps): add grind rails to the east deck ledge`, which is why release-please produced a minor bump rather than a patch. It is an ancestor of the release commit 0f7b854 `chore(main): release 0.2.0 (#10)` (verified with `git merge-base --is-ancestor`), tagged v0.2.0. The GitHub Actions run for the release event is 42698987316 at 2026-11-09T21:04:28Z with gate, build and publish all `completed success`; a follow-up workflow_dispatch run 42700013105 at 21:10:44Z is also green. The published version's `date_created` is 2026-11-09T21:06:13Z, i.e. the package came from the TASK-056.06 pipeline, not a manual `tcli publish`.

Live package verification (AC #5): the Thunderstore experimental package API reports latest `pythoninthegrass-Megabonk_Level_Editor-0.2.0`, `is_active: true`, `is_deprecated: false`, dependency `BepInEx-BepInExPack_IL2CPP-6.0.788`, categories Mods/Tools. The published download was fetched from `https://thunderstore.io/package/download/pythoninthegrass/Megabonk_Level_Editor/0.2.0/` and lists exactly six entries: icon.png, README.md, manifest.json, and BepInEx/plugins/MegabonkLevels/{MegabonkLevels.Mod.dll, NLayer.dll, NLayer.LICENSE.txt}. Runtime-only contents with the BepInEx dependency intact.

Recorded finding, scope of delivery: the change itself is authored level and pack data (`levels/thps.mblevel.json`, 48 -> 53 edits, and `unity/pack-authoring/packs/thps/attachments.json`, 58 -> 63 attachments), and the runtime-only Thunderstore ZIP does not carry it - docs/thunderstore.md#content-and-licensing forbids levels, third-party packs and music, and extracted THPS assets in particular. So the east deck ledge grinds in the git checkout, in locally generated levels and in the piece-assembled Warehouse (verified in game, both the authored and the editable level), while a manager-installed 0.2.0 download cannot show the rail because it ships no level or pack at all. AC #4 and #5 are met as written (the change went out through release-please and the automated pipeline with runtime-only contents); the player-visible gap is the public-release content boundary that TASK-048.02 enforces, not a defect in this fix.

Stale note correction: the earlier entry here recorded `npm run test:site` failing with tests/site.test.js:37 expecting scripts/mcp_server.py on the showcase page. That no longer applies - site/tests/site.test.js:38 now asserts `doesNotMatch(/scripts\/mcp_server\.py/)`, and a fresh `mise exec -- task site:test` on main is green: 42 tests, 0 failures (log /private/var/folders/8h/syybw6g96b7330fq1hqlm0sr0000gn/T/opencode/site-test-060.log). Worth noting for the CI rescope: root `task check` runs build, installer:test, test and lint only, so it never runs the site's built-page tests - that is how a red site test survived here.

DoD #4 verified on the actual commit bodies: `feat(thps): add grind rails to the east deck ledge` (33ff224), `docs(backlog): record the east ledge rail fix on the grind task` (68cf2ff) and `docs(thps): record the east ledge grind check in the Warehouse layout` (f4906d6) are conventional subjects with no Co-Authored-By, Generated-with or tool/model attribution.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Made the east deck ledge rail beside the totem grindable, matching Shorty's ledge, and shipped the result as v0.2.0 through the automated Thunderstore pipeline.

Diagnosis: (27, 2, 27) stands on Shorty's ledge, whose top edge carries hidden game rails from LEDGE_LIPS; the matching raised block beside the totem at (162, 2, 65) had the mesh edge but no rail laid on it (nearest rail 14 units away). So the fix was missing rails, not a broken one.

What shipped:
- EAST_LEDGE_LIPS (5 segments, owner piece-ledge-east) added in scripts/build_thps_level.py after the start lip, so existing rail path indices 0-27 stay unchanged; added to COPING_LIPS, with COPING_OWNERS and the attachment path count in scripts/build_thps_attachments.py extended so the piece pack carries the new grind paths.
- Regenerated levels/thps.mblevel.json (48 -> 53 edits), unity/pack-authoring/packs/thps/attachments.json (58 -> 63 attachments) and the preservation baseline as a deliberate refresh.
- Docs: the east ledge check recorded in docs/thps-warehouse-layout.md; site docs synced.

Why: the two mirror-image ledges behaved differently, which read as a bug in the level rather than as authored data.

Tests were written first: 4 new tests in tests/test_build_thps_level.py assert EAST_LEDGE_LIPS joins end to end with gentle turns, is a subset of COPING_LIPS, its corners are corners of the mesh ledge runs, and that the rail at (162.57, 3.79, 64) exists.

Verification in the running game: with the slide held (grind_slide) on the regenerated authored level, 'grind started at (162.6, 7.7, 63.0) on the rail at (162.6, 3.7, 64.4)' and RailHandoff carried the grind onto the rail at (170.8, 3.8, 49.2), i.e. sustained across the chain; the west ledge still grinds at (25.8, 7.8, 38.0) with sparks. Releasing the slide blocks the start through the StartRail hook, same as the west ledge. The Unity pack bundle was then rebuilt (task thps:pack --force, both StandaloneWindows64 and StandaloneLinux64) and the piece-assembled levels/thps-editable.mblevel.json grinds on the east ledge too. The chain stops at (168.76, 3.79, 79.77) because the next mesh edge turns 90 degrees.

Release: 0.2.0 went out through release-please and the path-filtered automated workflow (gate, build, publish all green on the v0.2.0 release event), and the live package page serves 0.2.0 with runtime-only contents and the BepInExPack_IL2CPP 6.0.788 dependency.

Known limit, recorded rather than fixed here: the runtime-only package carries no level or pack, so the new rails are not reachable from a Thunderstore download - that boundary is TASK-048.02's policy, and closing it would need a public level/pack distribution route (the gallery, TASK-063.07).

Verification at closure: task check green on main (0 C# errors, 1552 Python tests passed, 6 skipped, ruff/markdownlint/deno clean) and task site:test green (42 pass, 0 fail); published ZIP contents and package metadata checked against the live Thunderstore API.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
