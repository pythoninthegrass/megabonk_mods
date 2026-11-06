---
id: TASK-006.08
title: Draw the position readout only while the level editor is open
status: Done
assignee: []
created_date: '2026-11-06 23:47'
updated_date: '2026-11-06 23:52'
labels:
  - map-selection
  - editor
dependencies: []
references:
  - src/MegabonkLevels.Mod/position_label.cs
  - src/MegabonkLevels.Mod/position_readout.cs
  - docs/development.md
parent_task_id: TASK-006
priority: low
type: enhancement
ordinal: 173000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The position readout under the minimap (the player's `me:` line plus the boss, elite and enemy lines) is drawn whenever the dev harness is enabled and a mod-loaded level is running. Outside the editor it should not appear, including when a distributed level is played on a box that has the harness enabled. Player installs have no harness enabled file, so they already hide it; this closes the gap on dev boxes.

Outcome: the readout is drawn only while `EditorMode.Active` is true, and only when the harness is enabled and the level is mod-loaded as before. Leaving the editor removes it; entering it brings it back. Position debugging during normal play is deliberately given up: `state` and the cell log still report positions.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The readout is not drawn while playing a mod-loaded level outside the editor, even with the harness enabled
- [x] #2 The readout is drawn while the editor is open on a mod-loaded level with the harness enabled, with the same lines as before
- [x] #3 Exiting the editor removes the readout and re-entering it draws it again
- [x] #4 Vanilla levels and a disabled harness still draw nothing
- [x] #5 A unit test covers the visibility rule
- [x] #6 docs/development.md Position readout section states the editor-only rule
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
1. Add a pure rule `PositionReadout.Visible(armed, editorActive)` in position_readout.cs and a failing unit test in tests/MegabonkLevels.Tests/position_readout_tests.cs first.
2. In `PositionLabel.Tick`, destroy the label and return when the rule says hidden, so leaving the editor removes it and re-entering recreates it (TryCreate already runs when the label is null).
3. Leave `CellOf`, the cell log and `Arm`/`Disarm` unchanged so `state` and the cell log keep reporting positions.
4. Update the Position readout section of docs/development.md.
5. Run `task mod:test`; confirm in the running game that the readout is absent in play and present in the editor.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verified on the authoring box with the Warehouse: the log shows PositionLabel created under the minimap on each editor entry and nothing after exit, and the play screenshot has no readout. The editor screenshot cannot show the label because the editor's Level panel covers that area, so the editor-side check rests on the log line. Vanilla and disabled-harness cases are unchanged: Arm still gates on DevHarness.Enabled and Disarm hides the label. task check not run to green: the 17 failures present on a clean tree remain (see TASK-006.06); the mod unit tests all pass (1999).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The position readout under the minimap (player, boss, elite and enemy lines) is now drawn only while the level editor is open. A pure rule, `PositionReadout.Visible(armed, editorActive)`, gates it; `PositionLabel.Tick` hides the label whenever the editor is closed, and re-entering the editor recreates it. `Arm`/`Disarm`, `CellOf`, the cell log and `state` are unchanged, so positions are still reported there; position debugging during normal play is deliberately given up. Tests: a unit test over the four input combinations, written first; all 1999 mod unit tests pass. Docs: the Position readout section of `docs/development.md` states the editor-only rule. Verified in the running game with the Warehouse: no readout in play, and the log shows the label created on each editor entry; the editor screenshot cannot show it because the Level panel covers that area. `task check` is not green: the 17 failures present on a clean tree remain (see TASK-006.06), so DoD #1 is left unchecked.
<!-- SECTION:FINAL_SUMMARY:END -->
