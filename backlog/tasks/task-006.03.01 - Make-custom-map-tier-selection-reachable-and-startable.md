---
id: TASK-006.03.01
title: Make custom-map tier selection reachable and startable
status: Done
assignee: []
created_date: '2026-10-31T17:10:00Z'
updated_date: '2026-10-31T17:50:00Z'
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
- [x] #1 Warehouse can be selected and started through the normal Map Selection flow on wm2 with mouse and controller navigation.
- [x] #2 Custom-map selection never leaves focus on a hidden or blank tier option; its available tier is selectable and Confirm works.
- [x] #3 Switching between custom and native maps restores native tier availability and navigation without stale selection state.
- [x] #4 Regression coverage and a documented live wm2 verification include switching from a higher native tier to Warehouse and confirming that its level loads.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Reproduce the stock-menu failure on wm2 with remote screenshot/query diagnostics and OS-level mouse/gamepad input (no developer load); inspect native tier selection ordering.
2. Add failing regression tests for the tier-state/navigation repair, then fix custom tier availability, selection and focus at the correct menu lifecycle points while preserving native refresh behavior.
3. Build/deploy on wm2 using its mise SDK and installed interop assemblies; restart through Steam and verify mouse/controller starts, higher-native-tier → custom and custom → native transitions. No Unity editor or asset rebuild is required.
4. Document observed behavior and live verification, run task check, and commit conventionally. Leave any unverified acceptance criteria open with a precise blocker.

Final implementation keeps the native group's index layout intact, repairs navigation after every native tier refresh, selects/focuses Tier 1 only after the outer map handler, and snapshots/restores separately captured Navigation values before the next map selection. Final runtime checks passed; finish with conventional commits and sync the target checkout.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Reproduced on wm2 with OS-level uinput mouse/virtual Xbox controller; harness used only for screenshots and reflection queries, not load-level/editor navigation. Baseline Forest had Tier 3 selected; Warehouse hid it without selecting Tier 1. Initial repair enabled/selected Tier 1 and mouse Confirm loaded rendered Warehouse. Controller testing exposed native stats refresh overwriting the repaired navigation after tier selection; updated repair to relink on every RefreshTiers without shrinking/reindexing the native group mid-handler. Rebuilding and retesting this final variant now. Local task check passed before this refinement (1498 C# + 849 Python tests).

Final wm2 verification passed on the final runtime implementation. OS mouse clicks with X11 absolute positioning selected Forest Tier 3 → Warehouse → Tier 1 → Confirm and loaded rendered Warehouse. Virtual Xbox 360 D-pad/A completed the same menu path, including Tier 1 ↔ Challenges traversal and Confirm. After custom → native switching, a live query reported all Forest tiers canSelect=true with only Tier 3 selected; Graveyard retained one visible tier. Warehouse query reported first tier canSelect=true/isSelected=true and both hidden tiers false/false. Final controller run logged starting map=Forest stage=0 tier=0 seed=20261007 followed by KillFloor armed; screenshots show Warehouse/Tier 1 in both mouse- and controller-started runs. Evidence remains on wm2 as ~/mb-verified-*.png (notably verified-restored-tier3, verified-pad-confirm, verified-controller-warehouse, verified-mouse-native3, verified-final-mouse-pause).

Final task check passed: build, 1498 C# tests, 849 Python tests, markdownlint and Ruff. Tests were observed failing against hide-only behavior before implementing the repair; refresh-navigation regression also observed red before its fix. Existing nullable/pytest configuration warnings remain unchanged. docs/development.md documents lifecycle ordering, reference-backed Navigation copies, remote build steps and live verification. Game quit after testing, harness marker disabled back to its original state, and temporary virtual input devices stopped. No Unity editor, asset rebuild, save reset or developer load was used.

Implementation committed as f59d865 (fix: repair custom map tier selection and navigation).

Post-commit checkout sync to wm2 completed cleanly at d568575. An additional full on-device task check built successfully and ran 1498 C# tests: 1488 passed, including the new tier regressions; 10 existing THPS fixture tests failed before Python/lint could run. Root cause verified in thps_level_tests.cs and thps_editable_level_tests.cs: root discovery searches for Taskfile.yml, while git tracks lowercase taskfile.yml. The case-insensitive macOS checkout passes all 1498 tests; wm2's Linux filesystem does not find that marker. This unrelated case-sensitive test portability issue is not changed in the menu fix. Local full task check and final live wm2 menu acceptance remain passed. No follow-up task created without approval.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Fixed custom-map tier availability, selection and controller focus in f59d865. Custom entries enable/select Tier 1, disable hidden tiers, repair explicit navigation on every stats refresh, and restore captured navigation before native map selection. Native group indexes remain stable during saved-tier restoration; interop Navigation snapshots are captured independently before mutation.

Verified on wm2 through normal mouse and virtual Xbox controller menus: Forest Tier 3 → Warehouse → Confirm loads rendered Warehouse; Tier 1 ↔ Challenges navigation works; returning to Forest restores all unlocked tiers and controller selection of Tier 3. No save reset, Unity editor or developer load required. Screenshots and live-query evidence are listed in implementation notes.

Three regression tests added first and observed failing before fixes. Final task check passed (1498 C# tests, 849 Python tests, build and lint). Development documentation updated with remote build instructions, lifecycle constraints and live verification. Game and temporary input devices stopped and original disabled harness-marker state restored after testing.

Additional on-device full-suite limitation: wm2 build passed and 1488/1498 C# tests passed (including all new regressions). Ten existing THPS tests fail because they search for Taskfile.yml rather than the tracked lowercase taskfile.yml on a case-sensitive filesystem; Python/lint were not reached on that run. This unrelated portability issue was left unchanged. Full local task check remains green.
<!-- SECTION:FINAL_SUMMARY:END -->
