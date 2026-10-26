---
id: TASK-005.11
title: Collapsible compact palette with expand control
status: To Do
assignee: []
created_date: '2026-10-26T20:33:00Z'
updated_date: '2026-10-26T20:38:00Z'
labels:
  - level-editor
dependencies:
  - TASK-005.08
references:
  - docs/development.md
  - src/MegabonkLevels.Mod/editor_palette.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
parent_task_id: TASK-005
priority: medium
type: enhancement
ordinal: 67000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005, TASK-005.08 and the "Catalog palette" section of docs/development.md first.

The palette (TASK-005.08) is a 4-column icon grid with a category tab column, a title, a search field and a page footer. It takes a large share of the left edge of the screen while the player is trying to see the map. The goal is more screen space on demand, with obvious UI cues for how to get the full palette and the search form back.

Behaviour requested by Lance:
- Expanded state: a double chevron `<<` on the right-hand side of the palette menu collapses it to a single column.
- Compact state: the chevron flips to `>>`, and a magnifying glass appears in the place where the "Search name or id..." input sits in the expanded state. Clicking the magnifying glass expands the palette again and focuses the search field. Clicking `>>` expands it too.

Decisions (answered and confirmed by Lance, see the notes): compact keeps the category tab column plus one column of slots, only as wide as the `<` and `>` buttons side by side with one slot above them; the column pages with the wheel and the single `<` `>` footer chevrons; the state resets to expanded on each editor entry; the magnifying glass focuses the search and expands; search and category stay applied while compact and are cleared manually.

Technical notes:
- `EditorPalette.Width` and `PointerOverPanel` are consumed by `editor_tile_tools.cs` (toolbar centring) and `editor_mode.cs` (look suppression). Both must follow the current state, so the toolbar re-centres when the width changes.
- Clicks are read from `EditorInput` through `EditorPalette.Tick`, not an EventSystem. The chevron and magnifying glass are click regions handled there.
- The compact state must not break the search/save keyboard capture or the three-step Esc sequence. Collapsing while the search field has focus must blur it through the shared `EditorEscapeSequence` path rather than leave focus on a hidden field.
- Whether a magnifying glass glyph exists in the game's RobotoMono TMP font asset is unconfirmed. If it does not, draw the icon from UI primitives or a small generated texture; prove the choice in the running game before building on it.
- Pure state and layout logic (compact flag, columns and slots per page for each state, page clamping after a state change so the selected entry stays visible) should live in a Unity-independent class with unit tests, like `PalettePager`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Lance's open questions in the description are answered and recorded in the task notes before implementation starts
- [ ] #2 A double chevron `<<` on the right-hand side of the expanded palette collapses it to a single column
- [ ] #3 In the compact state the chevron reads `>>` and the palette shows a magnifying glass where the search input is in the expanded state
- [ ] #4 Clicking the magnifying glass or `>>` returns to the full palette with its search field
- [ ] #5 The selected entry stays selected and visible (its page is shown) after collapsing and expanding
- [ ] #6 EditorPalette.Width and PointerOverPanel follow the current state, so the toolbar re-centres and map clicks and look are not blocked by the empty space left by the collapsed palette
- [ ] #7 Collapsing while the search field has focus ends focus cleanly and does not leave keyboard capture or the Esc sequence in a stuck state
- [ ] #8 Pure compact-state and paging logic is unit tested; docs/development.md Catalog palette section is updated
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-26: Lance answered the open questions. (1) Compact keeps the category tab column plus the first slot column, so category switching stays available. (2) The compact column can both scroll (wheel) and page with the single `<` `>` chevrons; both work. (3) The compact/expanded state resets to expanded on each editor entry. (4) Clicking the magnifying glass focuses the search field and expands. (5) An active search and category stay applied while compact and are cleared manually (Esc sequence / Delete in the field).

Interpretation to confirm when building: answer 2 read as wheel scrolling pages the compact column as it does the grid, plus the footer `<` `>` buttons, with no separate continuous scroll. Answer 5 read as the existing three-step Esc sequence and the Delete key clearing the search text; nothing clears the filters automatically on collapse.

2026-10-26: Lance confirmed the interpretations (1, 2, 5 all yes). Sizing for the compact state: the panel is only as wide as needed for the `<` and `>` buttons side by side with one slot column above them, so the compact width is about one slot plus margins, and the footer buttons set the minimum if they are wider than the slot. Wheel and the `<` `>` buttons page the column; filters stay applied and are cleared by hand.
<!-- SECTION:NOTES:END -->
