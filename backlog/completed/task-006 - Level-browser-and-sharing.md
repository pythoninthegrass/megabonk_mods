---
id: TASK-006
title: Level browser and sharing
status: Done
assignee: []
created_date: '2026-10-06 21:43'
updated_date: '2026-11-07 01:34'
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
Goal: let players discover and load levels other players made, and understand how to share their own, without Steam Workshop integration (that requires first-party support maintainer explicitly does not have). Sharing is file-copying: a player exports a `.mblevel.json`, sends it to someone else (Discord, a forum, a zip), and that player drops it into their own `UserData/Levels/` folder.

## Context

Discovery uses the game's own Map Selection screen, which lists every titled level in `UserData/Levels/` after the native maps (TASK-006.01). There is no separate browser. The player-facing documentation for sharing levels manually is TASK-006.02, since there's no automatic distribution channel yet (that's TASK-007's problem space if ever extended, and even then, custom asset packs still aren't Steam Workshop).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Players can find and start every titled level in UserData/Levels/ from the game's Map Selection screen
- [x] #2 A written guide explains how to install the mod (MelonLoader + this mod), and how to share a level file with another player manually
- [x] #3 The guide is discoverable from docs/ and linked from the main modding-setup doc
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Custom levels are discovered through the game's own Map Selection screen, which lists every titled level in UserData/Levels with its thumbnail, title and biome icon (TASK-006.01, .03, .05, .07). Players install through the packaged per-platform installers, with levels, sidecar images and asset packs travelling in the package (TASK-006.04, .06), and the plain-language guide docs/player-guide.md explains installing the mod and sharing a .mblevel.json by hand (TASK-006.02). The position readout is editor-only (TASK-006.08). Closed with DoD #1 unchecked: task check still reports 17 pre-existing pytest failures (installer parity, thps attachments/preservation) that fail identically on a clean tree; the Go installer is the source of truth and the Python installer is deprecated, so the parity failures are not being fixed.
<!-- SECTION:FINAL_SUMMARY:END -->
