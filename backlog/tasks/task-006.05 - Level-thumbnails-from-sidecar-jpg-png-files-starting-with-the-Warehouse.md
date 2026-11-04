---
id: TASK-006.05
title: 'Level thumbnails from sidecar jpg/png files, starting with the Warehouse'
status: In Progress
assignee: []
created_date: '2026-11-02T04:51:00Z'
updated_date: '2026-11-04 03:57'
labels: []
dependencies: []
parent_task_id: TASK-006
priority: medium
ordinal: 141000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Custom Map Selection entries show a flat purple placeholder thumbnail today: MapSelectionPatch clones mapEntryPrefab, calls MapEntry.Set with the base MapData, and sets the placeholder after overwriting name and description. When the editor ships to players, installed levels are loose data files, so a level's cover image has to ship as data too — the same model as runtime music (TASK-024): files discovered at startup from UserData with safe lookup rules, referenced by filename, nothing baked into the mod. Read a jpg/png sidecar named after the level file (same base name, next to the .mblevel.json in UserData/Levels) and show it as the entry's thumbnail. The Warehouse ships as the first consumer, and every future distributed level gets the mechanism for free; the level browser (this parent task) can reuse the same image later.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A level with a jpg/png sidecar (same base name as its .mblevel.json, in UserData/Levels) shows that image as its Map Selection thumbnail instead of the purple placeholder
- [x] #2 Discovery follows the mp3 runtime-catalog rules: case-insensitive extension matching, no path separators or traversal, and invalid or oversized files warn and fall back to the placeholder without breaking the entry
- [x] #3 A missing sidecar changes nothing: entries without an image look and behave exactly as today
- [x] #4 The Warehouse ships with a real thumbnail captured from the level, and its Map Selection entry shows it
- [x] #5 Sidecar naming, supported formats and size limits are documented in docs/level-format.md next to the music reference
- [x] #6 Verified in game with a harness screenshot: the Warehouse entry on the Map Selection screen displays the image
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. LevelThumbnailSidecar (pure logic): find <base>.png/.jpg/.jpeg next to the .mblevel.json, case-insensitive extension, skip reparse points, warn on ambiguity, size limit 8 MiB on disk (nonempty), 4096 px per side checked from header before decoding.
2. Tests first in tests/MegabonkLevels.Tests/level_thumbnail_sidecar_tests.cs (missing, each extension in mixed case, ambiguity, oversized, empty, reparse point, separators); run red, then implement.
3. map_selection_patch.cs: load bytes via ImageConversion.LoadImage with Il2CppStructArray<byte>; any failure warns and keeps the placeholder; cache per path and destroy with spawned clones. Spike LoadImage under Il2CppInterop first; if it cannot marshal, stop and ask before writing a managed decoder.
4. Warehouse: downscale .tools/evidence/warehouse-thumbnail.png to tile aspect and size limit, commit as levels/thps.png. Check packaging/installer path so the sidecar reaches UserData/Levels; report if changes outside ACs are needed.
5. docs/level-format.md: Level thumbnails section next to music reference.
6. Verify: task mod:build, relaunch, Map Selection harness screenshot of the Warehouse entry, task check.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Warehouse thumbnail captured with the clean-frame harness from TASK-006.05.01 (hud off, then screenshot) in the running thps level: 2560x1440 PNG at .tools/evidence/warehouse-thumbnail.png (gitignored, so it has to be copied into the repo as the Warehouse's sidecar before it ships). Framing: Tony McZoom on the board in front of the ramp, crane cabin and sponsor banners behind, no enemies or pickups, no HUD, readout or health bar. Not yet checked at Map Selection tile size, and 2560x1440 may exceed the size limit AC #2 will set, so it may need downscaling to fit. Sidecar location and filename for the shipped copy are still undecided (AC #1: same base name as the .mblevel.json in UserData/Levels).

Done so far: LevelThumbnailSidecar (level_thumbnail_sidecar.cs) with 28 passing tests, MapSelectionPatch.LoadThumbnail wiring, UnityEngine.ImageConversionModule reference, levels/thps.png (1280x720), docs section in level-format.md.

Blocker found in game: ImageConversion.LoadImage cannot be called through Il2CppInterop here. The generated wrapper constructs Il2CppSystem.Span<byte> from the array and throws ObjectCollectedException from Il2CppObjectBase.get_Pointer (stack: Il2CppSystem.Span`1..ctor <- ImageConversion.LoadImage(Texture2D, Il2CppStructArray<byte>, bool)). Same result with an explicit Il2CppStructArray kept alive. The entry falls back to the placeholder as designed. Needs a decision on a managed decoder before continuing.

Also observed: the native Map Selection tile is about 1.4:1, not wide, so the 16:9 image is stretched; the docs sentence about the tile shape is unverified and must be corrected.

Resolved the LoadImage blocker with NativeImageLoader: calls icall UnityEngine.ImageConversion::LoadImage_Injected via IL2CPP.ResolveICall with a pinned buffer in a 16-byte span wrapper and the native texture pointer from Object.m_CachedPtr (offset 0x10). The IL2CPP object pointer crashes the game at startup because InitButtons runs when the main menu is built. PNG and JPEG both verified in game (.tools/evidence/warehouse-map-selection-thumbnail-2.png, warehouse-map-selection-jpg.png). levels/thps.png is a 1080x720 center crop to match the roughly 3:2 tile. Unused ImageConversionModule reference removed.

task check: C# suite 1795 passed; pytest has 2 failures in tests/test_thps_pack_pieces.py (prefab piece set) that also fail with these changes stashed, so DoD #1 is left unchecked. Not committed yet.
<!-- SECTION:NOTES:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
