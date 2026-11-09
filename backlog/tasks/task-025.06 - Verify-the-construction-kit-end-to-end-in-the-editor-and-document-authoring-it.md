---
id: TASK-025.06
title: Verify the construction kit end to end in the editor and document authoring it
status: Done
assignee: []
created_date: '2026-10-30T16:24:00Z'
updated_date: '2026-10-31T17:06:00Z'
labels:
  - level-editor
  - thps
dependencies:
  - TASK-025.05
  - TASK-025.07
references:
  - scripts/mcp_server.py
  - scripts/run.py
  - levels/thps.mblevel.json
documentation:
  - docs/development.md
  - docs/thps-warehouse-pieces.md
  - docs/thps-warehouse-layout.md
parent_task_id: TASK-025
type: task
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Depends on TASK-025.05, which delivers the assembled editable level. Everything so far has been judged piece by piece; what has not been proven is that a person can actually rebuild the arena with the kit in the running game, and that nothing about the shipped level regressed once the editor starts handling dozens of interlocking pieces instead of one mesh. This task drives the whole workflow through the megabonk MCP harness and leaves the author-facing documentation behind.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A harness-driven walkthrough selects, moves, rotates, duplicates and deletes pieces in the editable level, then saves and reloads it with the changes intact
- [x] #2 Undo and redo restore every edit made in the walkthrough
- [x] #3 A ramp is rebuilt from composable modules in the editor and its joined surface rides and grinds continuously
- [x] #4 Performance and selection remain usable with the full set of pieces placed
- [x] #5 The shipped Warehouse level is re-verified unchanged and its gameplay re-checked through the harness
- [x] #6 Docs give an author-facing guide to the kit: the palette, module mating conventions, how to assemble and modify ramps, and the preservation guarantee for the shipped level
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
1. Prereqs: clean baseline — task check (incl. preservation check), pack installed, .env MEGABONK_DEV set. Unrelated pre-existing change in tests/test_player_installer_proton.py stays untouched.
2. AC1 walkthrough (one relaunch session on levels/thps-editable.mblevel.json): palette select (Tab:Packs, PaletteSearch, Palette:<id>), Place, Select, drag-move, R/F/G rotate, duplicate via second placement, Delete; assert via log_tail EditorObjectTools, state edit counts, screenshots. Save as scratch name thps-02506-walkthrough, reload, verify persistence.
3. AC2 undo/redo: interleave Undo/Redo (click_widget + Ctrl+Z/Y) after each edit incl. delete-restore and one settings-panel edit with its separate history; verify ui_tree enabled flags and restored state.
4. AC3 ramp rebuild: assemble butted main-transition modules + flat (or kicker pair) per the mating contract; verify riding continuity by gravity drop across seams with state() polling (no fall-through/kill floor) and grinding across the joint with grind_slide(held=true) + GrindAssist/RailHandoff log lines. Always hand back grind_slide auto at session end.
5. AC4 performance/selection with the full kit placed (editable level = full set): palette build/thumbnail log timings, save and load durations, selection pick path in dense stacks (raycast vs nearest); record numbers in task notes.
6. AC5 shipped level: uv run scripts/check_thps_preservation.py + task check; relaunch levels/thps.mblevel.json, ride/grind smoke test, Music/Radio log lines, KillFloor armed, no errors.
7. AC6 docs: author-facing kit guide appended into docs/thps-warehouse-layout.md (palette usage, mating conventions w/ links to pieces doc, worked ramp assembly from step 4, preservation guarantee link); cross-links from related docs.
8. Wrap-up: no new unit-testable logic (harness-driven verification; DoD note), task check + preservation check green, finalize per finalization guide, one conventional commit without attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
AC1+AC2 (editor session on levels/thps-editable.mblevel.json): raycast select, R rotate, drag-move (0.2 s hold), palette duplicate, middle-click pick-block and Delete all logged through EditorObjectTools (place/move/rotate/remove/selected lines). Walkthrough saved as thps-02506-walkthrough.mblevel.json (1447 edits) under UserData/Levels and reloaded; transforms verified via query_objects. Undo/redo proven per-edit and full undo-all/redo-all via click_widget(Undo/Redo) and the held-Ctrl chord (key down LeftControl, interleaved state() calls, Z/Y, key up); plain Ctrl+Z taps do not register under UndoRedoCtrlHoldSeconds=0.2f. Undo is strictly LIFO: dropping a buried edit needs undo-all-above + redo-all. Screenshots .tools/evidence/02506-01..02506-32.

AC3 (ramp rebuild): authored placements 32/34/38 removed; kit copies piece-main-south-02 (114.40,0,6.53), piece-main-south-01 (134.06,0,6.53) — seam pitch 19.66 vs authored 19.722656, coping joint gap 1.34 vs 1.403 — and piece-main-flat (110.14,0,-0.66), 0.95 short of the nominal z 0.285. Copings auto-attached (LiveEdit: attached added-grind-coping-1/0,/1). Saved thps-02506-ramp.mblevel.json (1451 edits); relaunch reloaded all three copies at exact saved transforms with KillFloor armed. Ride: drop on strip seam x=124.2 slid continuously over the toe/flat joint to rest (124.2,3.15,1.61), no catch. Grind: caught the west coping rail (114.4,10.6,17.9) eastbound and RailHandoff: moved onto rail at distance 0.00, progress 0.000, direction 1.0 onto (134.1,10.6,17.9) — continuous crossing at grind speed. Catch direction follows the approach side.

AC4: EditorPalette: rendered 277 thumbnails in 360 ms on editor entry; LiveEdit: applied 1447 edit(s) in ~40 ms at load; save wrote in 207 ms; dense-stack selection resolves via raycast or the nearest fallback within spacing/8. AC5: shipped levels/thps.mblevel.json relaunched — Music: using clip '04_Superman' (sourceIsPlaying=True), KillFloor armed, zero errors; authored-pipe grind continuous x 130.4->175.84; ride drops at x 129.64/139.5/149.36 all settle on the pipe flat bottom (y -3.01, z 28.84); music-probe radio-next logged Radio: playing '05_Jerry_Was_A_Race_Car_Driver.'; uv run scripts/check_thps_preservation.py green.

AC6: docs/thps-warehouse-layout.md gains the 'Authoring with the construction kit' subsection: palette usage (Packs tab, search append/Esc-Esc, thumbnail-click selects but does not arm Place, middle-click duplicate), the kept-cell (10,7) click constraint, mating conventions linked to the pieces doc mating contract (pivot-at-toe, pitch 19.722656, flat centre offset 6.245470), the verified ramp recipe with ride/grind outcomes, measured performance, and the preservation guarantee linked to development.md. DoD#2: no new unit-testable pure logic — harness-driven verification and docs only, no production code changes. task check: 849 passed + markdownlint + ruff clean.

Follow-up investigation (same day): the intermittent invisible-placed-piece observation is a placement-height artifact, not a rendering defect. query_objects showed freshly placed copies with Renderer enabled=true/isVisible=true at pivot y -20: Place takes Y from the kept tile surface, and the kept cell (10,7) sits at level -1 (20 units per level) under the hiding mesh, so fresh copies are buried 20 units below the visible Warehouse floor while colliders/selection stay live. The AC3 copies rode at y 0 because the tile had been raised one level during Raise-tool testing in that session. Reproduced with a fresh copy on the shipped editable level (bounds Center (133.55,-14.65,-5.01) from click (580,460)), then undone; the full kit renders correctly (bright overview screenshot .tools/evidence/02506-inv-07-fly1.png). Documented as 'Placement height - the invisible piece trap' in the author guide; no follow-up task needed (user chose investigate-then-decide).
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Verified the THPS construction kit end to end in the running editor through the megabonk MCP harness. A saved walkthrough proves select/move/rotate/duplicate/delete plus reload persistence; undo and redo restore every edit per-edit and wholesale (toolbar buttons and held-Ctrl chord). The main-pipe south half was rebuilt from two piece-main-south strips and piece-main-flat at kit pitch: it rides continuously across the strip seam and the toe/flat joint and grinds across the coping joint via RailHandoff, and a fresh relaunch reloads the saved transforms exactly. Full-kit performance measured: 277 palette thumbnails in 360 ms, 1,447 edits applied in ~40 ms, save 207 ms, selection usable in dense stacks. The shipped Warehouse is unchanged (preservation baseline green) with gameplay re-checked — ride, grind, music, radio, kill floor, zero errors. AC6 delivered as the new 'Authoring with the construction kit' section in docs/thps-warehouse-layout.md covering the palette, mating conventions (linked to the pieces doc), a worked ramp assembly and the preservation guarantee. No production code changed; DoD#2 is satisfied as no-new-testable-logic (harness-driven verification). The intermittent invisible-placed-piece observation was investigated to root cause afterwards: placement Y follows the kept tile's surface at level -1 (y -20) under the hiding mesh, so fresh pieces are buried below the visible floor while renderers stay live — a documented authoring gotcha, not a rendering bug; the guide now covers it and no follow-up task is needed.
<!-- SECTION:FINAL_SUMMARY:END -->
