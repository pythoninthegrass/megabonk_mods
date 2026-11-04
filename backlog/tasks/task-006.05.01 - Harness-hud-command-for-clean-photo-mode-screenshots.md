---
id: TASK-006.05.01
title: Harness hud command for clean photo-mode screenshots
status: Done
assignee: []
created_date: '2026-11-04 03:07'
updated_date: '2026-11-04 04:31'
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

Unblocked: the two tests/test_thps_pack_pieces.py failures were fixed by TASK-039 (41f53e7, skip the piece prefab tests when the build holds no prefabs). task check now exits 0 on a clean tree: mod build, installer tests, C# suite 1795 passed, pytest 1167 passed / 29 skipped, markdownlint and ruff clean. DoD #1 checked and the task closed.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Adds a harness HUD toggle so `freeze` + `camera` + `screenshot` produces a clean photo-mode frame, the first consumer being the Warehouse thumbnail in TASK-006.05.

**What changed**
- `harness_command.cs`: `HarnessCommandKind.Hud` plus a `TryParseEnabledFlag` case for `{"command":"hud","enabled":bool}`; a missing or non-bool `enabled` is rejected.
- `hud_visibility.cs` / `hud_control.cs`: `HudVisibility` bookkeeping saves the alpha the first time the HUD is hidden and restores exactly that value, so hiding twice does not overwrite the saved alpha and a HUD that was already faded before `hud off` stays faded after `hud on`.
- `dev_harness.cs`: the handler fades `UiManager.Instance.hudGroup` (stage clock, XP/HP bars, minimap, quest box, weapon icons, map title, and the position readout parented under the minimap) and the `CanvasGroup` of every active `HealthUI` with `followPlayer` set — the in-world health/shield bar sits outside the HUD group and the game's own `Update` does not override the alpha.
- `scripts/run.py`: `run.py hud <on|off>` with `build_hud_command`; `scripts/mcp_server.py`: typed `hud(on: bool)` tool.
- `docs/development.md`: harness command table row and a section covering behaviour, out-of-scope world-space elements, and the reset semantics.

**Behaviour**
An editor on/off round trip leaves the HUD hidden; a level load or new run builds a fresh HUD, so the HUD is visible again after `load` — documented rather than worked around.

**Tests**
Written first: C# parse tests for the `hud` payload and `HudVisibility` hide/hide-twice/show/no-op-show cases, plus Python tests for the `run.py hud on|off` payload. Verified in game against `levels/thps.mblevel.json`: hidden in a capture taken seconds after `hud off`, restored by `hud on`, hidden across an editor toggle, reset by a level load. `task check` passes on a clean tree (C# 1795, pytest 1167 passed / 29 skipped, lint clean).

**Commits**: a0108c2 and 74865f2.

**Follow-ups**: none open. Out of scope as recorded — world-space labels (enemy names, price tags, damage numbers, crown icons) and the level-up/pause/death screens are still drawn.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
