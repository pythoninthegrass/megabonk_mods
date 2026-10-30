---
id: TASK-024.04
title: Play runtime tracks as level and boombox music on default Wine
status: Done
assignee:
  - Assistant
created_date: '2026-10-30T02:24:00Z'
updated_date: '2026-10-30T15:18:00Z'
labels:
  - music
  - level-editor
dependencies:
  - TASK-024.03
documentation:
  - docs/music.md
  - docs/level-format.md
modified_files:
  - src/MegabonkLevels.Mod/level_music.cs
  - src/MegabonkLevels.Mod/level_music_reference.cs
  - src/MegabonkLevels.Mod/runtime_music_session.cs
  - src/MegabonkLevels.Mod/radio_playlist.cs
  - src/MegabonkLevels.Mod/megabonk_levels_mod.cs
  - src/MegabonkLevels.Mod/custom_level_state_patch.cs
  - src/MegabonkLevels.Mod/music_probe.cs
  - src/MegabonkLevels.Mod/harness_command.cs
  - scripts/run.py
  - tests/MegabonkLevels.Tests/runtime_music_session_tests.cs
  - tests/MegabonkLevels.Tests/level_music_reference_tests.cs
  - tests/MegabonkLevels.Tests/harness_command_tests.cs
  - tests/MegabonkLevels.Tests/MegabonkLevels.Tests.csproj
  - tests/test_run.py
  - docs/music.md
  - docs/level-format.md
  - docs/development.md
parent_task_id: TASK-024
ordinal: 123000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Players need to select discovered mp3s as stage music and cycle them with the boombox without rebuilding packs. Verify on this Mac using its default Wine setup, not an assumed CrossOver configuration.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Startup discovers UserData/CustomMusic mp3s and track:<filename without extension> selects stage music with case-insensitive lookup.
- [x] #2 Runtime boombox progression and natural track endings follow numeric order from the selected track and wrap.
- [x] #3 Missing, unreadable and undecodable tracks warn and fall back to stock audio without failing level loading.
- [x] #4 Existing bundle: stage music and pack playlists remain unchanged, confirmed in game.
- [x] #5 Default Wine playback, rapid switches, wrap, replay and music controls are verified; audible results requiring human confirmation are explicitly recorded.
- [x] #6 Reference parsing and integration policies have tests written first and music/level-format documentation describes folder, references, ordering and fallback.
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
1. Add failing tests for track: parsing and a Unity-independent runtime playlist session (selection, numeric successor/prefetch, wrapping, failure and disposal).
2. Integrate startup discovery, runtime session ownership and bundle-preserving playback in LevelMusic; release resources on replacement/menu/vanilla run/shutdown and fall back to stock on failures.
3. Run unit/build checks, exercise default Wine startup, stage/radio/wrap/replay/cleanup/fallback and bundle regression through the development harness, documenting source-state evidence separately from human listening.
4. Update music/level-format docs, run task check, review diff, commit conventionally, and finalize only criteria supported by evidence.

Live replay regression found that MusicController unloads generated runtime clip data on external takeover. Track external replacement and re-create the current runtime clip on the next stage selection; regression-test re-selection and verify tone takeover -> replay in Wine.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Tests-first: new parser/session tests initially failed to compile because runtime_music_session.cs did not exist; after implementation all 1359 xUnit cases passed. Added harness-action cases, observed four red parser tests before wiring radio-next/seek/menu-music/stage-music diagnostics.

Default Wine live evidence: startup discovered 20 files and case-insensitive track:14 strobe selected a playing 635.872s Strobe clip. Four-second fixture natural endings progressed ZZ Integration Wrap -> 00.01 -> 00.02 -> 00.10 -> 01 Police Truck, proving wrap/numeric order without forced seeking. Three consecutive boombox Interact calls advanced 02 -> 03 -> 04 with playing sources. A bad successor released the runtime session and started Forest stock music; OnMainMenu released session/prefetch and played Menu. Pause/unpause, held pitch 0.55, cutoff 400 and duck multiplier 0.2 source-state checks passed; overrides released. These are automated state checks, not human listening confirmation. Raw logs/results retained under .tools/evidence/music-integration/.

Initial fallback checks on default Wine: missing filename, chmod-000 discovered file and invalid MPEG each warned, retained levelLoaded/killFloorArmed/editor state and played Forest stock audio with runtimeSession=false. Bundle regression: Superman -> Jerry, seek near Jerry end -> 06_01_Screamer, successive Interact calls through 13_Le_Hot_99 -> 01_Police_Truck, and PlayStageMusic replayed previously unloaded Superman; menu cleanup then played Menu.

Replay test exposed Unity unloading generated clip data after another track takes over: tone takeover -> stage replay originally left sourceIsPlaying=false. Fixed by marking external replacements and rebuilding current runtime selection on stage lookup. Retested Strobe -> tone -> Strobe and Police Truck -> tone -> Police Truck: playing=true with time advancing (0 -> 0.51s), without crash. Added re-selection regression plus cancellation/join and missing/permission-denied session tests. Runtime real-library wrap 14 Strobe -> 01 Police Truck and end progression -> 02 Here and Now verified. Live AudioClip query after switching found only the current runtime clip, not previous clips or the managed-prefetched successor.

Temporary synthetic/bad/unreadable music fixtures removed; original soundtrack files retained and 14 Strobe installed in UserData/CustomMusic. No human listening confirmation was obtained for integrated playback, transitions, volume slider or natural ducking; docs explicitly distinguish source-state checks from the earlier shared-native-path listening evidence. Native Linux remains guarded for 024.05.

Final task check passed after replay fix: 1367 xUnit tests, 517 Python tests, build and markdownlint/ruff; git diff --check clean. Implementation committed as 485d6d4 (feat(music): integrate runtime tracks with stage and radio playback). AC5's audible-confirmation caveat is explicitly recorded above and in docs/music.md; automated verification is not represented as listening.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Integrated startup CustomMusic discovery and case-insensitive track: references with numeric radio/automatic progression, one-successor prefetch and lifecycle cleanup. Missing/unreadable/bad audio falls back to stock without failing level loading; bundle playlists remain separate. Fixed live-discovered runtime replay failure by rebuilding clips unloaded by external playback. Added tests-first parsing/session/harness coverage and updated music, schema and harness docs.

Verification: default Wine stage selection (Strobe), numeric natural endings, boombox rapid switches/wrap, runtime/bundle replay, menu cleanup, source controls, and missing/permission-denied/invalid-MPEG fallback. task check passes: 1367 C# + 517 Python tests and lint. Commit: 485d6d4.

Human listening of integrated audibility/transitions/volume slider/natural ducking is not newly confirmed; source-state verification and prior shared-native-path listening evidence are distinguished in docs. Native Linux remains guarded for the existing follow-up task.
<!-- SECTION:FINAL_SUMMARY:END -->
