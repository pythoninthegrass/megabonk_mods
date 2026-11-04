---
id: TASK-032.05
title: 'Editor: create a new from-scratch level and save its full state'
status: To Do
assignee: []
created_date: '2026-11-04 20:37'
updated_date: '2026-11-04 20:37'
labels: []
dependencies:
  - TASK-032.02
  - TASK-032.03
  - TASK-032.04
parent_task_id: TASK-032
priority: high
ordinal: 158000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Parent TASK-032. The editor can only edit on top of a generated map today: entering is refused unless a run is in progress, and Save writes only the edit list (EditorTileTools.Save in src/MegabonkLevels.Mod/editor_tile_tools.cs, LiveEditPatch.SnapshotLevelFile). It needs a way to start a blank from-scratch level and to save one.

New level: a command taking map, stage and grid size writes a minimal from-scratch file (a flat grid with the spawn and boss spawner on it) and loads it through the normal relaunch and load path; it does not mutate the live map. Expose it as an editor button, a dev harness verb, a run.py command and an MCP tool, following how the existing harness verbs are wired (harness_command.cs, dev_harness.cs, scripts/run.py, scripts/mcp_server.py).

Save for a from-scratch session writes the current tile state into the grid, folds object moves and removes into final placements, and writes spawn and bossSpawner from the player-start and boss-destination markers. The fold is a pure, tested function. The editor's load guard compares map, stage and tier and ignores the seed for from-scratch files. Write tests first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The editor button, harness verb, run.py command and MCP tool each create a blank from-scratch level and open it in the editor
- [ ] #2 A new level can be edited with the tile and object tools, saved, reloaded and shows the same grid and placements
- [ ] #3 A saved from-scratch file contains a grid, spawn and bossSpawner and no tile edit ops or gen: targets
- [ ] #4 Moving then removing a placed object saves as no placement; moving it saves one placement at the final position; covered by unit tests
- [ ] #5 Loading a from-scratch level inside the editor is not refused over a seed mismatch
- [ ] #6 Python tests cover the run.py and MCP wiring, in the style of the existing tests
- [ ] #7 docs/development.md documents the new-level workflow
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
