---
id: TASK-054.06
title: >-
  Console overlay renders no text: scrollback rows and input never generate TMP
  geometry
status: To Do
assignee: []
created_date: '2026-11-08T16:27:00Z'
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
- [ ] #1 Typed text, the placeholder and command output are drawn in the console in the running game, verified with a harness screenshot after running help
- [ ] #2 Scrollback rows report a real renderedWidth in query_objects while they hold text
- [ ] #3 The root cause is identified and recorded in docs/development.md, not just masked
- [ ] #4 A regression check exists where the logic is testable, or the cause is documented as only reproducible in the live game
- [ ] #5 Block caret, light grey placeholder behaviour, ? alias, history listing, clear and cross-session persistence are each confirmed on screen
- [ ] #6 The uncommitted overlay changes are committed with the fix
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
