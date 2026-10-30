---
id: TASK-024.04
title: Play runtime tracks as level and boombox music on default Wine
status: To Do
assignee: []
created_date: '2026-10-30T02:24:00Z'
labels:
  - music
  - level-editor
dependencies:
  - TASK-024.03
documentation:
  - docs/music.md
  - docs/level-format.md
parent_task_id: TASK-024
ordinal: 123000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Players need to select discovered mp3s as stage music and cycle them with the boombox without rebuilding packs. Verify on this Mac using its default Wine setup, not an assumed CrossOver configuration.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Startup discovers UserData/CustomMusic mp3s and track:<filename without extension> selects stage music with case-insensitive lookup.
- [ ] #2 Runtime boombox progression and natural track endings follow numeric order from the selected track and wrap.
- [ ] #3 Missing, unreadable and undecodable tracks warn and fall back to stock audio without failing level loading.
- [ ] #4 Existing bundle: stage music and pack playlists remain unchanged, confirmed in game.
- [ ] #5 Default Wine playback, rapid switches, wrap, replay and music controls are verified; audible results requiring human confirmation are explicitly recorded.
- [ ] #6 Reference parsing and integration policies have tests written first and music/level-format documentation describes folder, references, ordering and fallback.
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
