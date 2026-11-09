---
id: TASK-054.06
title: >-
  Console overlay renders no text: scrollback rows and input never generate TMP
  geometry
status: Done
assignee: []
created_date: '2026-11-08T16:27:00Z'
updated_date: '2026-11-08T16:33:00Z'
labels: []
dependencies: []
references:
  - src/MegabonkLevels.Mod/console_overlay.cs
  - src/MegabonkLevels.Mod/editor_ui.cs
  - src/MegabonkLevels.Mod/text_field_view.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
documentation:
  - docs/development.md
parent_task_id: TASK-054
priority: high
type: bug
ordinal: 197000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The in-game console opens, slides, shows its translucent panel and block caret, and runs commands, but no text is ever drawn: not the typed line, not the placeholder, and not any scrollback output. Commands do execute. `UserData/console_log.jsonl` records the inputs `help`, `?` and `history` and 122 output lines, including a correct numbered `history` listing, so the command layer, persistence and `ConsoleState.Plan` are fine. The defect is only in how the overlay's TextMeshPro labels are created or updated.

Evidence from the live game, via the harness `query_objects` on `TextMeshProUGUI`:
- The 16 scrollback labels (`Line0`..`Line15`) hold the correct text, are enabled, `isActiveAndEnabled` is true, colour is white and alpha is 1.
- Their `renderedWidth` and `renderedHeight` are the no-geometry sentinel (-4294967300). Every other active, non-empty label in the game, including the HUD ("LVL 1" at 47) and the editor's labels, has a real width. So the labels were given text but TMP never generated a mesh for them.
- The panel `Image` and the caret `Image` draw correctly (screenshot), so the canvas itself renders.

The labels come from `EditorUi.NewLabel`, the same helper the editor palette, tooltip, startup cover and menu notice use, and those draw. What differs for the console is unknown. Candidates to check first:
- The canvas root is deactivated by `ConsoleOverlay.Tick` when parked and reactivated on open, and the labels are created in `OpenConsole`/`Build` and then driven every frame; check ordering of creation, activation and the first text assignment.
- `editor_tile_tools.cs` calls `ForceMeshUpdate()` after setting label text; the console never does.
- The labels' parent rects (`Scrollback` and `Line{i}`) are sized with `PlaceTopLeft` before and after the panel is positioned; confirm they have a non-zero rect when TMP first lays out.
- `FixInputBaseline` and `TextFieldView` shift and re-measure the input label.

An attempted mitigation is in the working tree: scrollback rows set their text and call `ForceMeshUpdate()` only when the row's text changed. It builds and was deployed, but its effect on the live game was not confirmed.

Also in the working tree and uncommitted, from live testing of the overlay: the panel is now a single translucent dark grey image (alpha 0.72) instead of the shared opaque bordered fill, the input line sits at the top of the panel, the placeholder is its own light grey label that hides after the first typed character until the console is reopened, the caret is a block, `?` aliases `help`, `history` lists the remembered lines instead of clearing the scrollback, and history and scrollback persist in `UserData/console_log.jsonl` through `ConsoleLogStore`. Those changes are covered by C# tests and `task check` passes, but none of the on-screen text could be confirmed.

Note for verification: the running `megabonk` MCP server must be restarted to pick up the console keys (BackQuote, PageUp, PageDown, Home, End) before the harness `key` command can open the console; until then the console has to be opened by hand.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Typed text, the placeholder and command output are drawn in the console in the running game, verified with a harness screenshot after running help
- [x] #2 Scrollback rows report a real renderedWidth in query_objects while they hold text
- [x] #3 The root cause is identified and recorded in docs/development.md, not just masked
- [x] #4 A regression check exists where the logic is testable, or the cause is documented as only reproducible in the live game
- [x] #5 Block caret, light grey placeholder behaviour, ? alias, history listing, clear and cross-session persistence are each confirmed on screen
- [x] #6 The uncommitted overlay changes are committed with the fix
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
1. Root cause (confirmed live via query_objects): scrollback rows are LineHeight=20 px tall, the RobotoMono line at 16 pt is 21.1 px. With Ellipsis overflow and word wrap off, TMP finds no line fits (isTextOverflowing=true) and emits no glyphs, so renderedWidth/Height stay at the sentinel. Input label and placeholder draw because they use Overflow mode.
2. Fix in console_overlay.cs: raise LineHeight to 22 and give scrollback labels Overflow mode so row height can never cull text. Drop the ForceMeshUpdate mitigation if the fix works without it.
3. No unit-testable logic (font metrics exist only in the live game); document the cause and the live check in docs/development.md (AC4 alternative).
4. Rebuild, relaunch, verify on screen: help output, placeholder, block caret, ? alias, history, clear, persistence across relaunch; check renderedWidth of Line rows.
5. task check, commit (overlay changes already landed in 4d03861).
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Root cause: scrollback rows were 20 px tall (LineHeight) but the RobotoMono line at 16 pt is 21.1 px. With Ellipsis overflow and word wrap off, TMP reported isTextOverflowing=true and emitted no glyphs, so renderedWidth/Height stayed at the sentinel. The input line and placeholder drew because they use Overflow mode or taller rects; it was not an activation-order or ForceMeshUpdate problem.

Fix (console_overlay.cs): LineHeight 22, scrollback labels use Overflow mode, ForceMeshUpdate workaround removed. docs/development.md records the cause, the live check, and updates the stale panel-look description.

Verified live (relaunch, harness key/type/screenshot): help output, grey placeholder, block caret, ? alias, history listing, clear, and history restored after a relaunch all drawn; Line* rows report real renderedWidth. No unit test: font metrics exist only in the live game (documented). task check passes (1114 tests). The other overlay changes the task listed as uncommitted were already in 4d03861.
<!-- SECTION:FINAL_SUMMARY:END -->
