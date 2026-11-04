---
id: TASK-006.05.01
title: Harness hud command for clean photo-mode screenshots
status: In Progress
assignee: []
created_date: '2026-11-04 03:07'
updated_date: '2026-11-04 03:35'
labels: []
dependencies: []
parent_task_id: TASK-006.05
priority: medium
ordinal: 150000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The harness screenshot (MCP `screenshot`, `run.py screenshot`) reads back the whole rendered frame, so every capture includes the stock HUD (stage clock, XP, HP, minimap, quest box, weapon icons) and the mod's position/actor readout. That makes the captures unusable as level thumbnails, docs images or level-browser covers. Add a harness command that hides all of that on demand and restores it, so `camera` + `freeze` + `screenshot` yields a clean photo-mode image. The first consumer is the Warehouse thumbnail in TASK-006.05.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A harness command hides the stock HUD and the mod's position/actor readout, and a second command (or argument) shows them again; the MCP server and run.py expose it as a typed tool/verb
- [x] #2 With the HUD hidden, a harness screenshot of the running Warehouse level contains no HUD elements and no readout text, verified by reading the PNG
- [x] #3 Showing the HUD restores every element that was hidden, including ones that were already hidden beforehand staying hidden
- [x] #4 The hidden state survives a level load or editor mode toggle without leaving the game stuck without a HUD, or the doc states clearly that it is reset
- [x] #5 Command name, arguments and behaviour are documented in docs/development.md next to the other harness commands
- [x] #6 Pure logic (command parsing, hide/restore bookkeeping) has tests written first
- [x] #7 With the HUD hidden, the in-world player health bar under the character is also hidden and is restored by hud on
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first: C# parse tests for {"command":"hud","enabled":bool} -> HarnessCommandKind.Hud (reject missing/non-bool enabled); HudVisibility bookkeeping tests (hide, hide twice keeps original alpha, show restores, show with nothing saved is a no-op); Python tests for run.py hud on|off payload and parsing.
2. Mod: add HarnessCommandKind.Hud, TryParseEnabledFlag case "hud", dev_harness handler setting UiManager.Instance.hudGroup.alpha to 0 and back via HudVisibility; PositionLabel sits under the minimap so it is covered, hide it explicitly if a screenshot shows otherwise.
3. Scripts: run.py hud <on|off> with build command and subparser; MCP hud(on: bool) tool.
4. Verify in game: relaunch, load levels/thps.mblevel.json, hud off, screenshot, read PNG, hud on and confirm restore; check behaviour across level load and editor toggle (AC #4), document if it resets.
5. Docs: hud entry in docs/development.md next to the other harness commands.
Out of scope: in-world labels (enemy names, price tags, damage numbers, crown icons); level-up/pause/death screens.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Committed a0108c2: hud command hides UiManager.hudGroup (HUD, minimap, position readout, map title). Verified in game: hide, restore, editor on/off keeps it hidden, level load resets it to visible. Remaining: in-world player health bar under the character is outside hudGroup; ACs #1-#3, #5, #6 covered by a0108c2 pending the health bar AC. task check blocked by two pre-existing failures in tests/test_thps_pack_pieces.py.

Health bar: HealthUI instances with followPlayer set carry their own CanvasGroup outside hudGroup; hud now fades those too. Verified in game: bar hidden in a capture seconds after hud off (Update does not override the alpha) and restored by hud on. DoD #1 left unchecked: task check stops on two failures in tests/test_thps_pack_pieces.py that also fail on a clean checkout; lint and the C# tests pass.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
