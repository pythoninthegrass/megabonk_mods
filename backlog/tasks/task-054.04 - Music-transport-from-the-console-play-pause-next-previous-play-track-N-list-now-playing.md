---
id: TASK-054.04
title: >-
  Music transport from the console: play, pause, next, previous, play track N,
  list, now playing
status: To Do
assignee: []
created_date: '2026-11-08T07:54:00Z'
labels: []
dependencies:
  - TASK-054.01
  - TASK-054.02
references:
  - src/MegabonkLevels.Mod/radio_playlist.cs
  - src/MegabonkLevels.Mod/level_music.cs
  - src/MegabonkLevels.Mod/runtime_music_session.cs
  - src/MegabonkLevels.Mod/custom_music_library.cs
  - src/MegabonkLevels.Mod/music_probe.cs
  - scripts/run.py
  - scripts/mcp_server.py
documentation:
  - docs/development.md
parent_task_id: TASK-054
priority: medium
type: feature
ordinal: 195000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The maintainer asked for console control of music playback, such as prev/pause/play/next and "play track 12". Custom levels can play a soundtrack in two ways: a pack playlist (`bundle:<pack>/<clip>`, for example the THPS OST) or runtime mp3 tracks (`track:<name>` from `UserData/CustomMusic`). Today a track only advances when the current one loops, or when the in-level boombox is interacted with. There is no way to go back, jump to a numbered track, pause, or see what is playing. The playlist model can only peek at and advance to the next clip.

Verbs. None are gated: they are harmless and available to every player. Track numbers are 1-based in playlist order.
- `music.play`: resume paused music.
- `music.pause`: pause the current music.
- `music.next`: go to the next track.
- `music.prev`: go to the previous track.
- `music.track n`: jump to track n.
- `music.list`: numbered list, with the current track marked.
- `music.now`: current track name and number.

Behaviour on a stock stage, where there is no custom playlist: `music.play`/`music.pause` still pause and resume the game's music. `next`/`prev`/`track`/`list` reply `no custom playlist on this stage` instead of failing silently. Changing tracks from the console must leave the automatic advance-on-loop and boombox behaviour consistent: the next automatic advance continues from the track chosen in the console.

For harness and MCP parity, the same operations should be reachable as a harness command, so agents can verify them without the console UI. The console verbs bind to it through the TASK-054.02 registry.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The playlist model supports previous, select-by-1-based-index (rejecting out-of-range), count, ordered names and current index, with tests written first, including wrap-around at both ends
- [ ] #2 music.next, music.prev and music.track n change the playing track for both pack playlists and runtime mp3 playlists, and the log records the new track
- [ ] #3 After a console track change, the next automatic loop advance or boombox interaction continues from the chosen track
- [ ] #4 music.pause and music.play pause and resume playback on custom and stock stages
- [ ] #5 music.list prints a numbered list with the current track marked; music.now prints the current name and number
- [ ] #6 On a stock stage, next/prev/track/list reply 'no custom playlist on this stage'
- [ ] #7 A harness command (with run.py and MCP wrappers and pytest coverage of the payloads) exposes the same operations
- [ ] #8 Verified in game on a level with a pack playlist (e.g. the THPS Warehouse) and one with runtime tracks; docs/development.md music section documents the verbs
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
