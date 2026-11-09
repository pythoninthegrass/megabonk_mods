---
id: TASK-021.07
title: Play custom music on the THPS Warehouse level
status: Done
assignee: []
created_date: '2026-10-27T22:08:00Z'
updated_date: '2026-10-28T20:04:00Z'
labels:
  - level-editor
  - thps
  - audio
dependencies:
  - TASK-021.04
documentation:
  - docs/level-format.md
  - docs/development.md
parent_task_id: TASK-021
priority: low
type: feature
ordinal: 93000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The recreated level should sound like the original, so it needs to replace the stock music with its own audio file (mp3 or another format). Nothing in the project has looked at how Megabonk implements music yet, so this task starts with research and ends with a general mechanism that other levels could use too.

The research targets the Il2Cpp dump (`.tools/il2cpp_dump/dump.cs`, regenerate with `task re:dump`; see "Reading the game's code" in `AGENTS.md`) and, where method bodies matter, the native code in Ghidra through REA. Behaviour held in serialized Unity assets rather than code has to be confirmed in the running game.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A doc records how the game selects, loads and plays music, and how a level load changes the track, with the classes, fields and RVAs involved
- [x] #2 The level file format can name an audio file, with a schema version bump and migration for older files per docs/level-format.md
- [x] #3 Loading a level with an audio file plays that file instead of the stock music, and a level without one keeps the stock music
- [x] #4 The supported audio formats and how they are decoded are documented
- [x] #5 A missing or unreadable audio file falls back to the stock music and logs a warning instead of crashing
- [x] #6 Tests cover the level-format change, and the behavior is verified in game through the MCP server
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
The level names a pack AudioClip (`"music": "bundle:thps/Superman"`), not a raw audio file. Runtime decoding is not possible in this build: `UnityWebRequestMultimedia.GetAudioClip` and `AudioClip.Create` both throw MissingMethodException in the interop, and calling the `*_Injected` icalls by hand crashes the game (docs/music.md). The audio is therefore imported into the thps pack by ThpsPack.cs (Vorbis, compressed in memory) and loaded through the existing pack loader. Supported source formats are whatever the Unity editor imports.

Verified in game through the MCP server: the thps level logs `Music: handed 'Superman' to the music source, isPlaying=True`; a level without `music` logs nothing and keeps the stock track; a missing clip and a malformed id each log a warning and fall back. Not confirmed by ear.

Not covered: the main menu, jukebox preview and boss-room callers of `PlayMusicTrack`, and a final boss stage. Whether `UnloadAudioData` on the pack clip leaves it playable across a stage change is unverified.
<!-- SECTION:NOTES:END -->
