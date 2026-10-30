---
id: TASK-024
title: >-
  Load custom music from mp3 files at runtime for stage music and the boombox
  radio
status: To Do
assignee: []
created_date: '2026-10-29 08:43'
updated_date: '2026-10-30T01:16:00Z'
labels:
  - music
  - level-editor
dependencies: []
references:
  - TASK-021.07
  - TASK-021.07.01
documentation:
  - docs/music.md
  - src/MegabonkLevels.Mod/radio_playlist.cs
  - src/MegabonkLevels.Mod/level_music_reference.cs
  - unity/pack-authoring/Assets/Editor/ThpsPack.cs
priority: low
ordinal: 116000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Let a player add their own music to a custom level by dropping mp3 files into a folder, with no Unity install and no pack build. Today the only way to get a clip into a level is to import the mp3 into a Unity pack (`ThpsPack` imports `tools/ost/*.mp3` as Vorbis AudioClips into the `thps` bundle) and reference it from the level's `music` field as `bundle:<pack>/<clip>`. The boombox radio (`RadioPlaylist`, TASK-021.07.01) plays the pack's clips in clip-name order. Lance decided on runtime injection, not a generalised build-time pack: the mod itself reads and decodes the mp3 files in the running game.

Scope: discover mp3 files in a folder under UserData, order them by their leading track number (for example `01 Police Truck.mp3`, `06.01 Screamer.mp3`, `06.02 Nothing To Me.mp3`), let a level name one of them as its stage music, and let the boombox radio cycle through them in that order. Existing `bundle:` music references and pack clips must keep working unchanged.

Open questions for the implementer to settle and record in docs/music.md: which mp3 decoder works inside the Il2Cpp game on both CrossOver and native Linux (this is the main risk, so spike it first); whether tracks are decoded up front or streamed, given a playlist can be 14 tracks of about 3 minutes each; whether the folder is global or per level; how a level refers to a runtime track in its `music` field; and how files without a track prefix are ordered.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 mp3 files placed in the custom music folder are discovered at game start without Unity or a pack build
- [ ] #2 Tracks are ordered by their leading track number, including dotted numbers such as 06.01 and 06.02, and a file without a prefix has a documented, tested position
- [ ] #3 A level's music field can name a runtime-loaded track and it plays as that level's stage music
- [ ] #4 The boombox radio on a level plays the runtime tracks in prefix order and wraps after the last one
- [ ] #5 A missing, unreadable or undecodable file logs a warning and falls back to the stock audio without failing the level load
- [ ] #6 Existing bundle:<pack>/<clip> music references and pack playlists behave as before
- [ ] #7 Decoding works in the running game on CrossOver (macOS) and on native Linux, confirmed by playing a track on each
- [ ] #8 The prefix parsing and ordering logic is unit tested and docs/music.md describes the folder, the naming rule and the level reference
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Output decision from TASK-024.01: prefer NLayer decode -> real runtime AudioClip -> existing MusicTrack/PlayMusicTrack path. Correct native creation is proven on the Win64 player under Wine: Construct_Internal() GC-handle unmarshal, m_CachedPtr as injected-call self, pinned UTF-16/PCM blittable spans. Lance confirmed clear relative-mp3 playback in THPS, natural menu/item ducking, held source pitch/tempo and low-pass modulation. Do not build a software pitch/duck/filter engine based on the earlier callback conclusion; those one-shot pitch/filter tests were inconclusive because game updates reset controls. Native Linux still requires ABI inspection and audible verification; the diagnostic currently guards it out. See docs/music.md for exact evidence and remaining production requirements.
<!-- SECTION:PLAN:END -->
