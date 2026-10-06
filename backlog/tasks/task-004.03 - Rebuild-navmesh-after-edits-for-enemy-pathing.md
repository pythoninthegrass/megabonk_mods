---
id: TASK-004.03
title: Rebuild navmesh after edits for enemy pathing
status: To Do
assignee: []
created_date: '2026-10-06 21:42'
labels:
  - level-editor
dependencies:
  - TASK-004.02
parent_task_id: TASK-004
priority: high
type: feature
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-004 first for full context.

Using TASK-002.03's confirmed findings on whether/how Megabonk bakes a NavMeshSurface (or whatever pathing mechanism it actually uses — TASK-002.03 may have found something other than NavMeshSurface), trigger a rebuild/rebake of the navigation data after TASK-004.02's edits are applied, so enemies can path onto tiles that were added, moved, or had height/slope changed, and do NOT path onto tiles that were removed.

If TASK-002.03 found that Megabonk does NOT use a rebuildable navmesh (e.g. pathing is some other mechanism, or baked at build time with no runtime rebuild hook), this subtask's scope changes to: investigate and implement whatever mechanism IS needed for edited tiles to be pathable, documenting the actual approach used (this may require more investigation than a simple "call rebuild" — flag this risk to Lance if the mechanism turns out to be substantially harder than expected, rather than shipping a level editor where enemies get stuck on edited terrain).

Verify with a real playthrough: edit a level to add a new path, move an enemy spawn point or let enemies naturally path toward the player across an edited tile, and confirm no enemies become stuck.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Navigation data is rebuilt/rebaked after edits are applied, using whatever mechanism TASK-002.03 confirmed the game actually uses
- [ ] #2 Enemies successfully path onto added or height/slope-modified tiles in a real playthrough
- [ ] #3 Enemies do not attempt to path onto removed tiles
- [ ] #4 If the confirmed mechanism differs substantially from a simple NavMeshSurface rebuild, the actual approach is documented and any added risk/complexity is flagged
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
