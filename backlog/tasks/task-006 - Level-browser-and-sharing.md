---
id: TASK-006
title: Level browser and sharing
status: To Do
assignee: []
created_date: '2026-10-06 21:43'
updated_date: '2026-10-29T18:31:00Z'
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

Discovery uses the game's own Map Selection screen, which lists every titled level in `UserData/Levels/` after the native maps (TASK-006.01). There is no separate browser. The player-facing documentation for sharing levels manually is TASK-006.02, since there's no automatic distribution channel yet (that's TASK-007's problem space if ever extended, and even then, custom asset packs still aren't Steam Workshop).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Players can find and start every titled level in UserData/Levels/ from the game's Map Selection screen
- [ ] #2 A written guide explains how to install the mod (MelonLoader + this mod), and how to share a level file with another player manually
- [ ] #3 The guide is discoverable from docs/ and linked from the main modding-setup doc
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
