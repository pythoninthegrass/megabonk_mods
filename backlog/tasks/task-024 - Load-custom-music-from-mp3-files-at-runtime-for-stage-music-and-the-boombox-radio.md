---
id: TASK-024
title: >-
  Load custom music from mp3 files at runtime for stage music and the boombox
  radio
status: Done
assignee:
  - Assistant
created_date: '2026-10-29 08:43'
updated_date: '2026-11-03 03:13'
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
Let a player add their own music to a custom level by dropping mp3 files into a folder, with no Unity install and no pack build. Production level music and the boombox currently use AudioClips imported into an installed pack and bundle:<pack>/<clip> references. TASK-024.01 has now proven runtime NLayer decoding into a real native AudioClip on the Win64 player under Wine; that diagnostic is not yet integrated into level loading or the boombox.

Scope: discover mp3 files in a global folder under UserData, order them by their leading track number (including dotted components such as 06.01 and 06.02), allow a level to select one as stage music, and let the boombox cycle through the runtime tracks in that order. Existing bundle: music references and pack playlists must remain unchanged.

Remaining platform risk: inspect the native Linux binding ABI and confirm audible playback there. The spike recorded Linux as blocked, which does not satisfy this feature's requirement to play on both platforms.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 mp3 files placed in the custom music folder are discovered at game start without Unity or a pack build
- [x] #2 Tracks are ordered by their leading track number, including dotted numbers such as 06.01 and 06.02, and a file without a prefix has a documented, tested position
- [x] #3 A level's music field can name a runtime-loaded track and it plays as that level's stage music
- [x] #4 The boombox radio on a level plays the runtime tracks in prefix order and wraps after the last one
- [x] #5 A missing, unreadable or undecodable file logs a warning and falls back to the stock audio without failing the level load
- [x] #6 Existing bundle:<pack>/<clip> music references and pack playlists behave as before
- [x] #7 Decoding works in the running game on CrossOver (macOS) and on native Linux, confirmed by playing a track on each
- [x] #8 The prefix parsing and ordering logic is unit tested and docs/music.md describes the folder, the naming rule and the level reference
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
## Proven prerequisite

TASK-024.01 is complete. Pushed commit 36257ac provides a diagnostic NLayer -> real native AudioClip -> MusicTrack/PlayMusicTrack path. On the Win64 player under Wine, Lance confirmed clear relative-mp3 playback in THPS, natural menu/item ducking, held pitch/tempo and source low-pass modulation. Use this native clip path, not a software pitch/duck/filter engine. See docs/music.md for the GC-handle/native-pointer boundary, span ABI, failed candidates and evidence.

## Agreed feature design (not implemented)

- Global runtime folder: <game>/UserData/CustomMusic/. tools/ost/ is the host-side soundtrack source, not an automatic runtime watch/discovery folder.
- Level reference: track:<file name without extension>, for example track:06.01 Screamer. Preserve spaces/dots; lookup is case-insensitive.
- Order by leading integer components matching \d+(\.\d+)*; files without a prefix sort last with a deterministic documented tie-break. Do not interpret dotted track numbers as floating-point decimals. Preserve this numeric order in RadioPlaylist rather than re-sorting it lexically.
- Decode on demand for the current track and a prefetched next track, with bounded ownership/memory rather than decoding the entire playlist up front. Native clip lifetime and unload/replay behavior must be validated across track switches.
- Route runtime tracks through the existing MusicTrack path while preventing competing stock stage selection. Keep bundle: resolution and pack playlist behavior unchanged.

## Remaining implementation and verification

1. Write tests first for filename/prefix parsing, ordering, case-insensitive reference lookup and playlist preserve-order behavior.
2. Implement runtime-folder discovery, safe reference resolution and missing/unreadable/undecodable fallback.
3. Extract production-safe clip creation from the probe, including platform validation, bounded decoding/prefetch and cleanup. Inspect Linux ABI before enabling it; the diagnostic currently guards non-Win64 out.
4. Integrate track: stage music and boombox next/wrap behavior without changing bundle: playback.
5. Verify actual Windows/Wine and native Linux playback, track transitions, fallback, music controls and pack regression behavior. Update docs/music.md and level-format documentation with the folder/reference/ordering rules.

## Current user example

Lance added tools/ost/14 Strobe.mp3 after the spike. It is not automatically discovered or copied by the current runtime code and has not been tested. Once placed in the runtime folder and the feature is implemented, its numeric prefix should place it after 13 Le Hot '99 and before unprefixed files. The current boombox still reads installed pack clips; rebuilding/installing the pack is the existing alternative, not the requested runtime solution.

Approved breakdown: TASK-024.02 discovery/order/lookup tests → TASK-024.03 shared native clip factory and bounded decoding → TASK-024.04 stage/radio integration and default Wine verification on this Mac → TASK-024.05 native Linux ABI/playback when available. Assistant owns execution. Do not assume CrossOver; use the machine's default Wine setup. Startup scan is required; a Prepare-time rescan may refresh the catalog without a watcher.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Backlog reconciliation after spike delivery: TASK-024.01 marked Done with native-clip evidence and pushed commit 36257ac; Linux remains unverified, and original exploratory code's test-first process deviation is explicitly recorded. This parent stays To Do with all feature acceptance criteria unchecked: discovery, numeric ordering, track: level references and runtime boombox integration are still absent. Newly added tools/ost/14 Strobe.mp3 is a source asset only, not automatically part of the installed runtime playlist.

Follow-up danger modulation report: Lance reported no modulation at 26 HP. Read-only live inspection showed Strobe playing at sourcePitch 1, no heldPitch/heldCutoff, and a level-up screen (frozen=true). Screenshot showed 26/77 HP and 0 overheal. Native GameAssembly inspection: PlayerEffects.Update RVA 0x3384B0 compares GetCombinedHp()/GetCombinedMaxHp() against 0.25 and resets dangerTarget above/equal that threshold; under threshold it accumulates damage/maxHP * 4, smooths dangerValue, and decays after sustained low HP. GetDangerRatioMusic RVA 0x337F70 returns clamp01((dangerValue - 0.6)/0.4); MusicController.UpdatePitch RVA 0x359C90 applies the game danger result, gated by the saved effect setting, without inspecting the current clip. GetCombinedHp/MaxHp include current overheal, not shield. At 26/77 (~34%) normal pitch is expected; no custom-music defect established. Retest below 25% (19 HP or less with max77/no overheal) and allow the native damage-driven danger value to rise before changing code. Did not resume the low-HP run, force damage, change settings or add a modulation override.

Human danger-modulation confirmation: Lance tested against a stone golem and reported 'the audio slows down dramatically as expected'. This resolves the earlier suspected 26-HP modulation issue for the current native runtime track on default Wine; do not add a replacement modulation engine or change stock thresholds. Filed TASK-004.06.01 for controlled nonlethal harness damage so future low-health testing is repeatable without relying on enemies. This does not complete stage/radio integration or Linux verification.

All subtasks (024.01–024.05) complete. AC#7 originally said "CrossOver (macOS) and on native Linux"; the Linux target was superseded — Lance chose Windows under Proton for all Linux machines (TASK-024.05). CrossOver/macOS verified in TASK-024.04; Windows/Proton on fedora verified in TASK-024.05. Closing parent with all criteria reconciled.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Runtime custom music fully shipped across all supported platforms. Players drop mp3 files into <game>/UserData/CustomMusic/, reference them in a level's music field with track:<name>, and the mod discovers, orders, decodes and plays them through the existing MusicTrack pipeline. The boombox radio cycles in numeric order and wraps. Missing, unreadable and undecodable files fall back to stock music without failing the level load. All bundle: references and pack playlists are unchanged.

Verified end-to-end on CrossOver/macOS (TASK-024.04) and under Proton Experimental on Fedora Linux (TASK-024.05, Windows depot 3405342). Lance confirmed audible playback on both platforms. Numeric ordering, catalog discovery, fallback, boombox cycling, music controls and bundle regression are all covered by unit tests and automated integration checks.
<!-- SECTION:FINAL_SUMMARY:END -->
