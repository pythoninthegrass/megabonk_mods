---
id: TASK-006.07
title: >-
  Let a level supply its own Map Selection name and biome icon, starting with
  the Warehouse
status: Done
assignee: []
created_date: '2026-11-06 23:41'
updated_date: '2026-11-07 01:16'
labels:
  - thps-warehouse
  - map-selection
dependencies: []
references:
  - TASK-006.05
  - TASK-006.06
  - src/MegabonkLevels.Mod/map_selection_patch.cs
  - src/MegabonkLevels.Mod/level_thumbnail_sidecar.cs
  - scripts/build_player_package.py
  - docs/level-format.md
parent_task_id: TASK-006
priority: low
type: feature
ordinal: 172000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
With the Warehouse thumbnail in place (TASK-006.05, TASK-006.06), Map Selection still labels the selected Warehouse as "Forest" at the top right, and the biome icon thumbnails down the right-hand side show the stock biome types rather than anything about the level.

Outcome: a level can supply its own display name and its own biome icon, and Map Selection shows them in the top-right name and the right-hand biome thumbnail. The Warehouse is the first user: it reads "Warehouse" and shows a halfpipe image (a single halfpipe picture is enough; it need not be a faithful render). Nothing in the mod may special-case the `thps` level or the name "Warehouse". A level that supplies neither keeps today's behaviour.

Proposed shape, to confirm before implementing: an optional display-name field on the level file, and an optional biome icon as a sidecar image beside the level (for example `thps.biome.png` next to `thps.mblevel.json`), following the thumbnail sidecar pattern in `LevelThumbnailSidecar` so the package builder from TASK-006.06 can ship it with a small extension.

Not yet investigated: where the name and biome icon come from today (the stock map data the custom entry borrows, versus fields on the level), how the sidecar naming must differ from the thumbnail so the two never collide, and whether the level-format schema needs a version bump for the name field. Record the decision in this task before implementing.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Selecting the Warehouse on Map Selection shows "Warehouse" as the map name at the top right, not "Forest"
- [x] #2 The Warehouse's biome thumbnail on the right-hand side is a halfpipe image
- [x] #3 No code path special-cases the thps level or the name Warehouse; both values come from the level's own name field and sidecar icon
- [x] #4 A second test level with a different name and icon shows both on Map Selection with no code change
- [x] #5 A level with no name field and no icon sidecar, and every stock map, shows its existing name and biome icon unchanged
- [x] #6 A missing, oversize or malformed icon falls back to the stock biome icon and logs a warning, matching how bad thumbnails are handled
- [x] #7 The package builder bundles the biome icon next to its level and the installer places it in UserData/Levels, covered by a Python test
- [x] #8 docs/level-format.md describes the name field and the biome icon sidecar, and docs/player-installer.md mentions the icon alongside the thumbnail
- [x] #9 Verified in the running game with a screenshot of the Map Selection screen
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Findings: the top-right name is MapStatsInfoUi.t_mapName and the right-hand biome picture is MapStatsInfoUi.mapIcon, both set by the native SetConfig from the borrowed base MapData (hence "Forest"); the existing SetConfig postfix already runs for custom entries and blanks the records.

Decisions:
- Name: reuse the existing `title` field on the level file (already required to list a level, already in CustomMapEntry.Title). No new field, no schema bump.
- Icon: sidecar `<base>.biome.png|jpg|jpeg` beside the level. The stem `thps.biome` never equals the thumbnail stem `thps`, so the two lookups cannot collide.

Steps:
1. Tests first (C#): LevelThumbnailSidecar.Find gains an optional stem suffix; tests cover `.biome` lookup, no collision with the thumbnail, ambiguity, missing, oversize.
2. Implement the suffix in LevelThumbnailSidecar and share the decode/validate path in MapSelectionPatch.
3. Test first (Python): build_player_package.sidecar_image_names also returns `<base>.biome.*`; installer test mirrors the thumbnail one.
4. StatsConfigPostfix: for a custom entry set t_mapName.text to the title and mapIcon.texture to the biome icon when one loads; otherwise leave native values.
5. Add a halfpipe `thps.biome.png` to levels/ and build_thps_level / package inputs as needed.
6. Docs: level-format.md, player-installer.md.
7. Verify in the running game with a Map Selection screenshot; AC #4 with a second scratch level.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented (uncommitted): LevelThumbnailSidecar.Find takes a `.biome` stem suffix; MapSelectionPatch loads a per-entry biome icon and StatsConfigPostfix sets t_mapName to the title and mapIcon to the icon for custom entries; build_player_package bundles `<base>.biome.*`; levels/thps.biome.png added; docs updated. C# sidecar tests (32) and the builder/installer pytest pass. `task check` shows the same 17 pytest failures with and without this change (installer parity, thps attachments/preservation), so they predate it. Not yet done: AC #4 and #9 in-game verification; the authoring box (mf) has MelonLoader disabled and no thps pack, so it needs a Proton or CrossOver box.

Verified on the macOS Wine box: Warehouse showed its title and the halfpipe icon, a scratch second level showed its own title and a red-and-white icon with no code change, and Graveyard kept its native name, icon and records. The bad-icon fallback (AC #6) is covered by the sidecar unit tests and the shared load path, not exercised in game. `task check` still has 17 pre-existing pytest failures (installer parity, thps attachments/preservation) that fail identically without this change, so DoD #1 is left unchecked.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Map Selection now shows a custom level's title as the top-right map name and its `<level>.biome.png|jpg|jpeg` sidecar as the right-hand biome picture, applied in the MapStatsInfoUi.SetConfig postfix. The name reuses the existing `title` field (no schema bump). LevelThumbnailSidecar.Find takes a `.biome` stem suffix so the icon reuses the thumbnail checks without colliding with it; the player package builder bundles the icon with its level. The Warehouse ships a halfpipe icon cropped from an in-game frame. Nothing special-cases thps or Warehouse. Docs updated in level-format.md, player-installer.md and development.md.
<!-- SECTION:FINAL_SUMMARY:END -->
