---
id: TASK-006
title: Level browser and sharing
status: To Do
assignee: []
created_date: '2026-10-06 21:43'
labels:
  - level-editor
dependencies:
  - TASK-005
priority: medium
type: feature
ordinal: 29000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Goal: let players discover and load levels other players made, and understand how to share their own, without Steam Workshop integration (that requires first-party support Lance explicitly does not have). Sharing is file-copying: a player exports a `.mblevel.json`, sends it to someone else (Discord, a forum, a zip), and that player drops it into their own `UserData/Levels/` folder.

## Context

TASK-005.05 already built a basic save/load dialog inside the editor. This task extends that into a proper standalone browser (usable outside editor mode too, e.g. from a modded main-menu entry point) and writes the player-facing documentation for sharing levels manually, since there's no automatic distribution channel yet (that's TASK-007's problem space if ever extended, and even then, custom asset packs still aren't Steam Workshop).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Players can browse all levels present in UserData/Levels/ from a dedicated in-game browser UI, not just the editor's save/load dialog
- [ ] #2 Each browser entry shows at minimum the level's title/filename, map, and a gameBuildId-mismatch warning if applicable
- [ ] #3 A written guide explains how to install the mod (MelonLoader + this mod), and how to share a level file with another player manually
- [ ] #4 The guide is discoverable from docs/ and linked from the main modding-setup doc
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
