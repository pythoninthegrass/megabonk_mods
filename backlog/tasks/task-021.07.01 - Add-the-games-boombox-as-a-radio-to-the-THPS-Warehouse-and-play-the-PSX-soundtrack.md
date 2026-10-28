---
id: TASK-021.07.01
title: >-
  Add the game's boombox as a radio to the THPS Warehouse and play the PSX
  soundtrack
status: To Do
assignee: []
created_date: '2026-10-28T20:32:00Z'
updated_date: '2026-10-28T21:42:00Z'
labels:
  - level-editor
  - thps
  - audio
dependencies: []
documentation:
  - docs/music.md
  - docs/level-format.md
  - docs/development.md
parent_task_id: TASK-021.07
priority: low
type: feature
ordinal: 109000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The THPS Warehouse recreation plays a single song, Superman, fixed by the level's `music` field. The original game has a soundtrack of many songs, and the level should let the player trigger them from a radio in the world. The radio is an existing Megabonk item, the game's boombox interactable, not a new object to build. Superman stays the level's default music. The soundtrack songs are mp3s kept under `tools/`, which is gitignored: only `tools/Goldfinger - Superman.mp3` (plus its flac source) is there at the time of filing, so the work pulls in whichever mp3s are present when it is picked up, and the rest of the soundtrack has to be supplied. `docs/music.md` ("THPS soundtrack sources") lists the 14 tracks, their artists and the albums to source them from. Audio cannot be decoded at runtime in this build, so songs must ship inside the thps pack bundle; docs/music.md has the music mechanism and that constraint.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The THPS Warehouse contains the game's existing boombox as a radio, placed where the player can reach and interact with it
- [ ] #2 Superman still plays by default when the level starts, and levels without a radio are unaffected
- [ ] #3 Interacting with the radio plays a song from the THPS soundtrack instead of the boombox's stock audio
- [ ] #4 Every mp3 under tools/ at pack build time is available to the level from the thps pack, and the pack and level still build and load when none is present
- [ ] #5 A missing or unplayable song falls back to the stock behaviour with a logged warning and does not crash
- [ ] #6 Any level-file change has a schema version bump and a migration, per docs/level-format.md, and existing level files still load
- [ ] #7 New logic is covered by tests written first, and the radio and default music are verified in game through the MCP server
- [ ] #8 docs/music.md, docs/level-format.md and docs/development.md are updated, and the soundtrack mp3s stay out of git
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
