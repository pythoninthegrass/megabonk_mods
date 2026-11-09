---
id: TASK-051
title: Toggle the coordinate readout independently of editor mode
status: Done
assignee: []
created_date: '2026-11-07 03:06'
updated_date: '2026-11-07T18:47:00Z'
labels: []
dependencies: []
references:
  - src/MegabonkLevels.Mod/position_label.cs
  - src/MegabonkLevels.Mod/position_readout.cs
  - src/MegabonkLevels.Mod/dev_harness.cs
  - scripts/run.py
documentation:
  - docs/development.md
priority: medium
type: enhancement
ordinal: 188000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up to closed TASK-006.08; its parent TASK-006 is no longer available for new subtasks. Replace the editor-only coordinate restriction with an explicit independent F7 toggle. The maintainer needs coordinates while playing a custom level to report terrain holes without entering the editor. Retain the original coordinate display system: yellow text, native minimap anchoring, typography, dynamic columns and existing overlap. Preserve the harness/custom-level boundary and keep the preference off by default. Plateau geometry changes are outside this task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An explicit coordinate toggle can show or hide the readout during gameplay without entering the editor or changing pause/camera state.
- [x] #2 Editor entry/exit and HUD visibility changes do not silently reset the coordinate preference; default normal play remains uncluttered.
- [x] #3 The dev harness can explicitly turn coordinates on/off and report the state; existing state/cell logging and vanilla/disabled-harness behavior remain intact.
- [x] #4 Unit tests and documentation cover the toggle, and live testing verifies on/off behavior in play and editor on the authoring host.
- [x] #5 The original yellow minimap-anchored coordinate readout, formatting and placement are retained; the maintainer explicitly accepts its existing minimap/editor overlap.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Add test-first pure coordinate preference state (off by default, explicit set/toggle, no editor dependency) and focused-input hotkey guard.
2. Wire F7 and an enabled-flag coordinates harness command into PositionLabel. Keep the original minimap-letter clone, yellow monospace text, formatting, column sizing and anchoring. Editor entry/exit and HUD visibility never reset the preference; HUD hiding still hides its child label.
3. Add enabled/visible snapshot fields, run.py coordinates on/off and an MCP wrapper with parser/serialization/CLI/MCP tests. Preserve cell logging while the readout is off.
4. Build and deploy the mod/scripts to the active authoring host after checking unsaved edits; use a fresh process and verify the original display plus F7/harness on/off in play/editor and HUD off/on without changing camera/pause.
5. Run tests/lint, update docs, and record known baseline check failures. Do not change plateau geometry or synchronize the fleet.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Maintainer explicitly rejected the proposed independent bottom-right panel: the original coordinate display, including its minimap overlap, must be reinstated. The rendering changes were removed; only independent visibility controls/state/logging remain. First live tests proved F7 works outside the editor; repeating visual verification with the restored original rendering.

Implemented independent F7 visibility plus coordinates on/off in the harness, CLI and MCP. Defaults off for a new game process; editor transitions and HUD visibility never reset the preference. The original TryCreate rendering implementation, native minimap-letter clone, yellow monospace text, dynamic columns, font size and anchored position are unchanged. No bottom-right panel or extra coordinate canvas remains.

Built and deployed on the active authoring host after verifying the prior player was dead (HP 0) and the editor had 102 clean/saved edits. Fresh-process live testing verified default off, explicit on/off, F7 outside the editor, unchanged frozen/editor/player state during toggles, and HUD off reporting enabled=true/visible=false followed by HUD on restoring visible=true. The final screenshot visibly shows the original player/enemy coordinate rows under the minimap. The maintainer was actively viewing/controlling the game during verification; no geometry changes were made.

Tests: all 2020 C# tests pass; all 515 CLI/MCP tests pass; mod builds on the maintainer and authoring hosts; lint passes. Full task check still has the same 17 unrelated installer-parity/THPS fixture failures, with 1302 Python tests passing and three skipped. Those baseline failure families were independently reproduced before this task. Changes are uncommitted, and the task remains In Progress for the full-check/commit completion items.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added an independent F7 coordinate toggle plus a harness/CLI/MCP `coordinates on|off` command. The preference is off by default and survives editor entry/exit and HUD visibility changes. The original yellow minimap-anchored readout is unchanged. Snapshots report enabled and visible. C# and CLI/MCP tests pass and live testing was done on the authoring host. Full `task check` still shows the same 17 unrelated installer-parity/THPS fixture failures as the baseline, so DoD #1 is left unchecked.
<!-- SECTION:FINAL_SUMMARY:END -->
