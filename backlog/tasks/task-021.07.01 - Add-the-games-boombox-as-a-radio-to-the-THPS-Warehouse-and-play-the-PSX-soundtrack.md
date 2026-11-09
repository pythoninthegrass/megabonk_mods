---
id: TASK-021.07.01
title: >-
  Add the game's boombox as a radio to the THPS Warehouse and play the PSX
  soundtrack
status: Done
assignee:
  - claude
created_date: '2026-10-28T20:32:00Z'
updated_date: '2026-10-28T23:16:00Z'
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
- [x] #1 The THPS Warehouse contains the game's existing boombox as a radio, placed where the player can reach and interact with it
- [x] #2 Superman still plays by default when the level starts, and levels without a radio are unaffected
- [x] #3 Interacting with the radio plays a song from the THPS soundtrack instead of the boombox's stock audio
- [x] #4 Every mp3 under tools/ at pack build time is available to the level from the thps pack, and the pack and level still build and load when none is present
- [x] #5 A missing or unplayable song falls back to the stock behaviour with a logged warning and does not crash
- [x] #6 Any level-file change has a schema version bump and a migration, per docs/level-format.md, and existing level files still load
- [x] #7 New logic is covered by tests written first, and the radio and default music are verified in game through the MCP server
- [x] #8 docs/music.md, docs/level-format.md and docs/development.md are updated, and the soundtrack mp3s stay out of git
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Soundtrack source moved to tools/ost (14 mp3s; filename = soundtrack order, tag = source album). Clip asset name = file name without extension, so the Superman clip becomes "04 Superman" and the level's `music` reference must change to it (default stays Superman).
2. Boombox prefab: the game's only InteractableBoombox asset is `BoomboxQuest`, held by `EffectManager.boomboxQuest` (confirmed live via query_objects). Add catalogId `interactable/boombox` (CatalogRoute kind Boombox, resolved from EffectManager) and palette entry. No new level-file field: a PlaceObject of that id is the radio, so no schema bump is needed (AC6 satisfied by not changing the schema).
3. Pack build: ThpsPack.SaveMusic imports every mp3 under tools/ost (override -musicSource as a directory) instead of the single Superman file; still builds with none present.
4. Mod: Harmony patch on InteractableBoombox.Interact for custom runs. Radio plays the next clip of the level's music pack (ordered by clip name) on the MusicController source via a MusicTrack, replacing the stock boombox audio; missing/unplayable clip logs a warning and falls through to stock behaviour.
5. build_thps_level.py: place the boombox in the Warehouse, switch music to the 04 Superman clip.
6. Tests first: CatalogRoute parse of interactable/boombox, palette entry, track-ordering/next-clip logic (pure C# in tests project), build_thps_level.py placement. Then in-game verification via MCP.
7. Docs: music.md, level-format.md, development.md.

Final approach differs from steps 4 and 5 above: the radio does not swap the boombox's own AudioSource. A Harmony prefix on InteractableBoombox.Interact skips the stock method (single-use, throws NullReferenceException when run twice) and plays the next pack clip through MusicController.PlayMusicTrack, so it replaces the level music. RadioPlaylist starts at the first clip (01 Police Truck) and wraps. The radio is placed at (90, 35.9, -122) on the start half pipe's top platform, height taken from the Warehouse mesh. LevelMusic's clip name for the default is 04_Superman (file names sanitised to [A-Za-z0-9_] because catalogId segments reject spaces). The pack loader pins prefabs and clips with HideFlags.DontUnloadUnusedAsset, because the game's unused-asset unload was destroying the Warehouse prefab and 13 of 14 clips.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Verification: task check passes (1139 C# tests, 428 Python tests, lint). In game via MCP and by hand: log shows 'Music: using clip 04_Superman' at load (default); boombox spawns at the planned position; user pressed the radio repeatedly and confirmed it plays in soundtrack order starting with Police Truck, replaces the level music globally, and stays pressable. Fallback: built the pack with -musicSource /nonexistent/ost (builds, Warehouse only), installed it, relaunched: log 'Packs: loaded pack thps with 1 prefab(s) and 0 clip(s)' then 'Music: no clip 04_Superman in pack thps; using the stock music.', level loaded, no crash; full pack restored afterwards. The Radio-specific warning paths (no playable clip, exception) are not exercised in game. No level-file schema change: the radio is an ordinary object.place of interactable/boombox, so AC 6 needs no bump or migration. Pack manifest version bumped to 2.0.21.

Not done: the stock boombox's animation, effects and any quest credit are skipped on the radio path. docs/music.md also carries the user's own soundtrack-table edits, committed with the feature.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added the game's boombox (interactable/boombox, EffectManager.boomboxQuest) to the THPS Warehouse as a radio. Pressing it plays the next soundtrack clip from the thps pack as the level music, in file-name order starting with 01 Police Truck, and wraps; Superman (04_Superman) remains the level's default music. ThpsPack now imports every mp3 under tools/ost (names sanitised to underscores) and still builds with none present. New logic: CatalogRoute Boombox kind, palette entry, RadioPlaylist (tests written first), build_thps_level.py radio placement, pack version 2.0.21. Also fixed the pack loader so bundle prefabs and clips are not reclaimed by the game's unused-asset unload. No level-file schema change. Docs updated: music.md, level-format.md, asset-bundles.md, development.md. Verified with task check and in the running game; the no-mp3 pack fallback was exercised in game. Risks: the stock boombox interaction (animation, effects, any quest credit) is skipped on the radio path; the radio's own warning paths are not exercised in game.
<!-- SECTION:FINAL_SUMMARY:END -->
