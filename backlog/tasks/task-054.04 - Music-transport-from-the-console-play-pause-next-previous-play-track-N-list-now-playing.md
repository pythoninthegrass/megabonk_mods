---
id: TASK-054.04
title: >-
  Music transport from the console: play, pause, next, previous, play track N,
  list, now playing
status: Done
assignee: []
created_date: '2026-11-08T07:54:00Z'
updated_date: '2026-11-08T18:28:00Z'
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
- [x] #1 The playlist model supports previous, select-by-1-based-index (rejecting out-of-range), count, ordered names and current index, with tests written first, including wrap-around at both ends
- [x] #2 music.next, music.prev and music.track n change the playing track for both pack playlists and runtime mp3 playlists, and the log records the new track
- [x] #3 After a console track change, the next automatic loop advance or boombox interaction continues from the chosen track
- [x] #4 music.pause and music.play pause and resume playback on custom and stock stages
- [x] #5 music.list prints a numbered list with the current track marked; music.now prints the current name and number
- [x] #6 On a stock stage, next/prev/track/list reply 'no custom playlist on this stage'
- [x] #7 A harness command (with run.py and MCP wrappers and pytest coverage of the payloads) exposes the same operations
- [x] #8 Verified in game on a level with a pack playlist (e.g. the THPS Warehouse) and one with runtime tracks; docs/development.md music section documents the verbs
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. RadioPlaylist (tests first in radio_playlist_tests.cs): track an explicit current index; add Previous(), Select(oneBased) (null on out-of-range), Count, Names, CurrentNumber; Next/Previous wrap; Next after Previous/Select continues from the chosen track (AC1, AC3).
2. RuntimeMusicSession: PlayPrevious, PlayTrack(n), Names, CurrentNumber over the same playlist, so prefetch follows the chosen track (tests in runtime_music_session_tests.cs) (AC2, AC3).
3. Harness command `music` with action play|pause|next|prev|track(n)|list|now: HarnessCommand parse + tests, dev_harness dispatch to LevelMusic.Transport, which returns a JSON result (names, current, count) and logs the new track; pause/play drive MusicController.musicSource so stock stages work; playlist ops reply `no custom playlist on this stage` when none (AC2, AC4-AC6).
4. Console verbs music.play/pause/next/prev/track n/list/now (ungated) in console_command_registry.cs with registry tests; console reply text via ConsoleState.ReplyFor.
5. run.py `music` subcommand + build_music_command, MCP `music` tool, pytest coverage of the payloads (AC7).
6. docs/development.md music section: verbs and harness command (AC8).
7. Build with task mod:build, verify in game: THPS Warehouse (pack playlist, `task game:editor -- levels/thps.mblevel.json` / relaunch) and a level with a track: reference; check log lines and loop-advance continuity (AC8).
<!-- SECTION:PLAN:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added music transport. RadioPlaylist gained Previous, Select(1-based, null when out of range), Names, Count and CurrentNumber, with wrap at both ends and Next continuing from the chosen clip; RuntimeMusicSession exposes the same (PlayPrevious, PlayTrack, Names, CurrentNumber). A `music` harness command (play|pause|next|prev|track n|list|now) dispatches to LevelMusic.Transport, which reuses the boombox/loop-advance playback path so automatic advance continues from the console choice; play/pause drive the music source so they also work on stock stages; list/now/next/prev/track reply `no custom playlist on this stage` when there is none. Console verbs music.* are ungated and bind to it; ConsoleState.ReplyFor prints a result's `message` text. run.py `music` subcommand and MCP `music` tool added with pytest coverage; docs/development.md has a Music transport section.

Verified in game (relaunch, run.py music): THPS Warehouse (41-clip pack playlist): now/list/next/prev/track, wrap 41->1 and 1->41, out-of-range rejected, pause/play flip sourceIsPlaying, boombox and a seeked loop end both continued from the console-chosen track. Runtime-track level (scratch-minimal with track:01 Police Truck): same checks plus loop advance. Stock level without music: next/prev/track/list/now give the no-playlist reply, pause/play work. Console UI typed `music.list`, `music.pause` on a stock stage and `music.track 7`/`music.list` in the Warehouse and printed the replies.

Not verified: the F-key/console path with a gamepad, and audibility (checked by source state and log, not by ear).
<!-- SECTION:FINAL_SUMMARY:END -->
