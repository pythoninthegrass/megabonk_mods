---
id: TASK-005.07
title: 'Palette search, category tabs and tooltips'
status: Done
assignee: []
created_date: '2026-10-10 06:23'
updated_date: '2026-10-26T19:58:00Z'
labels:
  - level-editor
dependencies:
  - TASK-005.02
references:
  - docs/development.md
  - src/MegabonkLevels.Mod/editor_palette.cs
  - src/MegabonkLevels.Mod/palette_catalog_builder.cs
modified_files:
  - src/MegabonkLevels.Mod/editor_palette.cs
  - src/MegabonkLevels.Mod/palette_filter.cs
  - src/MegabonkLevels.Mod/palette_search_input.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
  - src/MegabonkLevels.Mod/editor_mode.cs
  - src/MegabonkLevels.Mod/editor_ui.cs
  - src/MegabonkLevels.Mod/editor_escape_input.cs
  - src/MegabonkLevels.Mod/editor_escape_sequence.cs
  - src/MegabonkLevels.Mod/editor_pause_input_patch.cs
  - src/MegabonkLevels.Mod/editor_text_input_policy.cs
  - tests/MegabonkLevels.Tests/palette_filter_tests.cs
  - tests/MegabonkLevels.Tests/palette_search_input_tests.cs
  - tests/MegabonkLevels.Tests/editor_escape_sequence_tests.cs
  - tests/MegabonkLevels.Tests/editor_text_input_policy_tests.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - docs/development.md
parent_task_id: TASK-005
priority: medium
ordinal: 47000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-005 and the "Catalog palette" section of docs/development.md first.

TASK-005.02 gives the editor a scrolling text list of every placeable prefab for the current map, grouped by stage and category (`PaletteCatalogBuilder`). For a large catalog that is slow to browse. Lance pointed at the Minecraft "Better Creative Mode" mod as the model: a text search box that filters entries live, category tabs, and a hover tooltip that shows the item name and its id.

Whether this pays off depends on catalog size. Before starting, read `EditorPalette: built <n> entries for <map>` in `MelonLoader/Latest.log` for a few maps and record the counts in the task notes. If they are small (a few dozen), say so and ask Lance whether to proceed.

Constraints carried over from the palette:
- Input is read from Unity's `Input` directly, not through a UGUI `EventSystem`, so the game's Rewired input module stays untouched. Text entry has to follow the same rule (`Input.inputString` is available).
- Editor mode binds W/A/S/D/Space/Left Ctrl/Left Shift to the free-fly camera and the digit keys to tile tools (TASK-005.03). While the search box has focus those keys must type, not fly or switch tools.
- The palette is rebuilt on each editor entry; the filter state may reset then.

Thumbnails and an icon grid are a separate task.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A search box in the palette filters entries by display name and catalogId as the user types, case-insensitively
- [x] #2 While the search box has focus, typed keys do not move the camera or switch editor tools; Esc or a click outside the box ends focus
- [x] #3 Category tabs (or equivalent toggles) built from the existing stage/category groups restrict the list to one group, with an All option
- [x] #4 Hovering an entry shows a tooltip with its display name and catalogId
- [x] #5 Selection still works on filtered results, and a selection hidden by a filter stays selected
- [x] #6 Pure filtering and focus logic is unit tested; docs/development.md Catalog palette section is updated
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
1. Measure live catalog sizes and confirm proceeding for modest catalogs (Forest 75, Desert 73; approved).
2. Add test-first pure filtering, grouping, focus, game-menu guard and Escape-sequence tests.
3. Add live name/id search, All/group controls and name/id tooltips while preserving hidden selections; use higher-contrast search styling and fixed search/save text baselines.
4. Share keyboard suppression across both forms, guard the confirmed PauseUi.Toggle cancel path, and preserve editor cursor ownership. For a form with text, Esc blurs, then clears, then opens the menu; an empty focused/pending form lets Esc open the menu immediately.
5. Update docs, run task check, verify runtime behavior plus user native-input confirmation, commit and close.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-10: Forest (seed 20261007) palette logged `EditorPalette: built 75 entries for Forest`. Other maps not measured yet.

2026-10-26: Started; dependency 005.02 completed. Measured stageIndex=0, tier=0, seed=20261007: Forest 75 entries (fresh relaunch succeeded); Desert 73 entries (Latest.log repeatedly recorded EditorPalette: built 73 entries for Desert). Desert relaunch helper failed after readiness retries despite building the palette; this is not a successful end-to-end check. Catalogs are modest, roughly 70 entries. Paused for Lance to confirm proceeding per task description. No implementation changes or criteria checked. Existing untracked task-015 and scratch level files left untouched.

2026-10-26: Lance approved proceeding despite the modest catalog sizes. Continuing with the recorded implementation plan.

2026-10-26: Implemented live case-insensitive name/catalogId search, stage/category cycling with a direct All reset, empty-result feedback and name/id hover tooltip. Existing rows are hidden/relaid out without replacing the full PaletteSelection catalog. Search focus state captures keyboard through the blur frame; shared editor guard suppresses camera/look/centering, tool digits, object shortcuts and undo/redo while search or save text is active. No EventSystem/Rewired changes. Updated Catalog palette docs.

Verification: wrote filtering/focus tests before implementation; initial task mod:test failed on missing PaletteFilter/PaletteSearchInput types. Added 13 test cases and verified task check passes: mod build, 703 C# tests, 185 Python tests, markdownlint and ruff. git diff --check passes.

Runtime verification on fresh Forest relaunch: rOcK showed only rock names; FOREST/SHRINES matched the five shrine ids despite case; selecting filtered rock_medium_01 showed name + forest/stage0/randomMapObjects/3/0 tooltip, and remained selected while hidden by shrine/group filters. While focused, held W/Space and tapped Alpha1/C left camera framing and Select unchanged. Escape ended focus; clicking group controls outside search ended focus and subsequent Alpha2 selected Lower. Stage 0 flat tiles showed only its nine entries; incompatible query/group showed No matching entries; previous-group from All wrapped to Interactables; All reset restored the full catalog and selection highlight. No ERROR/Exception lines in the current launch log. Screenshots are under the approved temporary directory: palette-name-filter-focus.png, palette-selected-tooltip.png, palette-id-filter-hidden-selection.png, palette-group-no-results.png, palette-flat-group.png, palette-interactables-wrap.png and palette-all-restored.png.

Implementation committed as fb2f89e (feat(editor): add palette search, group filters and tooltips), with no attribution. All six acceptance criteria and four Definition of Done items verified.

User reports adding k to roc moves the search text vertically, and real Escape opens the game menu and hides the cursor while a form is focused. User explicitly requested the same guard for the level-save form. Reopened to fix and verify the keyboard-focus criterion against native game input.

Follow-up implementation: added a Harmony prefix to the unique PauseUi.Update method (dump RVA 0x5570B0), bypassing game menu input while EditorMode.Active and the existing shared search/save text capture guard is true. Rewired and EventSystem remain untouched. Both fields and save placeholder now use BaselineLeft with a fixed offset instead of MidlineLeft geometry centering. Kept requested opaque header/search backgrounds and white search text.

Follow-up verification: wrote five game-menu policy tests first (confirmed missing-type compilation failure), then task check passed with 708 C# tests and 185 Python tests plus build and lint. Fresh relaunch succeeded. Paired screenshots palette-fixed-baseline-roc/rock.png and save-fixed-baseline-roc/rock.png show no movement of the existing roc glyphs when adding k. Native Esc/menu and cursor behavior is not yet verified: harness key injects editor-only input, so it cannot exercise the game menu; host System Events discovery timed out. Await user confirmation with physical Escape in each field before rechecking AC2 and closing. Changes currently uncommitted.

User confirms physical Esc still opens menu. Targeted Capstone disassembly establishes UiManager.Update (RVA 0x55EEE0) reads MyInputManager UICancel/UIAbort at static offsets 0x98/0xA0 via GetButtonDown and calls PauseUi.Toggle (RVA 0x557050). PauseUi.Update only reads MapOverlay (offset 0x50) to switch windows, so the prior prefix could not intercept cancel. WindowManager.RefreshCursor (RVA 0x39E650) can hide/lock the cursor when there is no active game window; editor cursor ownership must override that refresh.

Replaced ineffective PauseUi.Update prefix with a PauseUi.Toggle prefix on the confirmed native cancel path. Added WindowManager.RefreshCursor prefix to keep cursor visible/unlocked throughout active editor mode; normal gameplay/menu behavior is unchanged when editor/text capture is inactive. Suppressed real menu toggles now log EditorTextInput: suppressed game menu toggle while typing for verification. Updated docs to explain the actual handler. task check passes (708 C# tests, 185 Python tests, build/lint); fresh Forest editor relaunch succeeded with no Harmony/ERROR/Exception lines. Awaiting physical Escape confirmation in search and save before closing.

Lance requested first Escape blur, second clear, third game menu. Applying the same sequence to search and level-save forms.

2026-10-26: Implemented shared EditorEscapeSequence and runtime routing: first Esc blurs preserving text, second clears that same form even if empty, third passes through to game menu; refocus starts at blur. Guard records consumed frames to cover game/editor Update ordering. Added test-first sequence/reset/refocus tests and external search-blur coverage. task check passes: 714 C# tests, 185 Python tests, build, markdownlint, ruff; git diff --check passes. Fresh editor relaunch succeeded, harness screenshots confirm search blur/clear and save blur. Lance confirmed the behavior works and explicitly requested checking ACs and marking Done; native-input verification is now accepted. All six acceptance criteria verified.

After confirming the three-step sequence and requesting task closure, Lance refined it: an empty form must let the first Escape trigger the game menu. Applying this before final commit/closure.

Final refinement implemented and tested: relevant empty search/save form immediately allows the game menu on Escape, including an empty pending-clear form. Content of the other form never causes an empty form to consume Escape. The consumed-frame guard still blocks the same press that clears text, so clearing does not also open the menu. Added focused-empty/pending-empty/unrelated-content tests before implementation; final task check passes 717 C# tests, 185 Python tests, build and lint. Latest build was deployed and freshly relaunched into Forest editor. Prior live behavior/user confirmation and all six AC checks retained; final empty-form policy is covered by pure tests.

Follow-up committed as d8eb1ad (fix(editor): stabilize text fields and handle form escape sequences), no attribution. All ACs and DoD items checked. Marked Done following user confirmation and final empty-form refinement.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Completed live case-insensitive name/id search, All/stage-category filtering and hover tooltips while preserving hidden selections. Both search/save forms suppress editor shortcuts, use stable text baselines, and share Escape handling: with text, blur then clear then menu; empty forms open the menu immediately. Guard targets the native PauseUi.Toggle path and preserves the editor cursor. Increased palette header/search opacity and made search text white. Updated docs; test-first logic coverage. Verified task check: 717 C# tests, 185 Python tests, build and lint, plus harness runtime checks and user confirmation of native-input behavior. Original implementation fb2f89e; follow-up fixes d8eb1ad. Thumbnails/icon grid remain out of scope.
<!-- SECTION:FINAL_SUMMARY:END -->
