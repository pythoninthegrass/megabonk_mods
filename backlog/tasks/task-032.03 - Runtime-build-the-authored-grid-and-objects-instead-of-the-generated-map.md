---
id: TASK-032.03
title: 'Runtime: build the authored grid and objects instead of the generated map'
status: To Do
assignee: []
created_date: '2026-11-04 20:37'
updated_date: '2026-11-04 20:37'
labels: []
dependencies:
  - TASK-032.01
  - TASK-032.02
parent_task_id: TASK-032
priority: high
ordinal: 156000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Parent TASK-032. When a loaded level is from-scratch (format subtask), the game must build the authored grid and objects and show none of the stock map's generated tiles, props or interactables, with no generate-then-tear-down pass.

Approach follows the spike's go/no-go: if go, replace the generator's output with the authored grid using the game's own tile instantiation, skip the generated object phases, and place the spawn portal and boss spawner at the authored positions before they are instantiated where the game allows. If no-go, generate the stock map and clear it in one step under the startup cover.

Constraints from existing work: the startup gate and cover (src/MegabonkLevels.Mod/startup_gate.cs, startup_cover.cs) exist because the generated spawn portal moves the player to a cached baseline position after the mod places them; for a from-scratch level the portal must land at the authored spawn, so the final placement is a no-op when the player is already in place. Keep the gate and do not fork it. A death-screen restart (MapController.RestartRun) is a second startup and must still work. Generated-baseline levels must be untouched. Reuse TilePlacement and the slope conventions in edit_operations.cs. Keep pure layout logic (cell to tile arguments, slope direction, size cap) Unity-free and unit tested; write those tests first.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Loading a from-scratch level shows only the authored tiles and placed objects; no generated props, chests, shrines or tile objects exist in the scene
- [ ] #2 The player starts at the authored spawn with no spawn reset and no visible stock-map flash
- [ ] #3 The boss spawner exists at the authored position and spawns a boss that can reach ground
- [ ] #4 A grid larger than the kit's stock size is refused at load with a logged reason
- [ ] #5 A death-screen restart returns the player to the authored spawn
- [ ] #6 Generated-baseline levels, including levels/thps.mblevel.json and levels/example-forest.mblevel.json, load exactly as before
- [ ] #7 Pure layout logic has unit tests written first, including a startup_gate case for the already-in-place spawn
- [ ] #8 docs/development.md and docs/runtime-map-structure.md describe the from-scratch load path
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
