---
id: TASK-018.02
title: Target editor widgets without guessing screenshot pixel coordinates
status: To Do
assignee: []
created_date: '2026-10-27T07:23:00Z'
labels:
  - dev-harness
  - tooling
dependencies: []
references:
  - src/MegabonkLevels.Mod/dev_harness.cs
  - src/MegabonkLevels.Mod/editor_tile_tools.cs
documentation:
  - docs/development.md
parent_task_id: TASK-018
priority: medium
type: enhancement
ordinal: 77000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Every `mouse` interaction needs guessed screenshot pixel coordinates. During TASK-016 AC#4, a click meant for the Save toolbar hit the terrain instead, repeatedly, because the toolbar sits in the top ~150px and the mod already knows its own widget geometry. Add a way to target widgets by name so an agent can click the Save button, Undo, or a palette entry without coordinate math, and a way to query what a pixel is over. Mod-side; verify in the real game.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A `click_widget(name)` tool clicks a named editor widget (Save, Undo, a palette entry) without pixel coordinates.
- [ ] #2 A `ui_tree`/`element_at` tool reports which widget a pixel is over, or lists the editor widgets and their rects.
- [ ] #3 Verified in the real game: click Save by name and confirm the save status changes.
- [ ] #4 docs/development.md documents the new tools; task check passes.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
