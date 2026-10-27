---
id: TASK-007.05
title: List pack bundle assets in the editor palette
status: In Progress
assignee:
  - '@claude'
created_date: '2026-10-26 23:05'
updated_date: '2026-10-27 06:02'
labels:
  - level-editor
  - assets
dependencies:
  - TASK-007.02
  - TASK-007.05.01
  - TASK-007.05.02
  - TASK-007.05.03
parent_task_id: TASK-007
priority: low
ordinal: 69000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Follow-up to TASK-007.02, building on the manifest from TASK-007.04. Loaded pack assets resolve through bundle: catalogIds but do not appear in the editor palette, so they are placeable only through the harness or a hand-written level file. Add palette entries (category, display name, thumbnail) for assets in installed packs under UserData/LevelPacks/.

## Decisions

- One `Packs` tab for all packs, not one tab per pack. The pack id is visible in the tooltip's catalogId and is searchable.
- A pack without a manifest, or with an invalid one, is listed from its bundle contents (the less strict behaviour, consistent with PackCatalog, which does not filter such a pack). Requiring a manifest is a possible later tightening.
- Entries are ordered by pack id, then asset name.

## Context

`PaletteEntry` is `(CatalogId, DisplayName, PaletteCategory, Stage)` and `PaletteCategory` is a fixed enum, so a `Pack` value is needed. `PaletteCatalogBuilder` builds only game-asset ids from counts, and `PrefabFor` in `editor_palette.cs` routes only game ids. `PackPrefabs.Resolve` returns a placeholder cube for a missing asset, which is wrong for listing, so listing needs a lookup that does not return placeholders. Thumbnails are cached by catalogId in `PrefabThumbnails`. Packs are not map-scoped, so their entries appear on every map.

Packs load once per session and the pack catalog caches misses, so a pack added after launch appears only after a relaunch; record this in the docs.
<!-- SECTION:DESCRIPTION:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A Pack palette category adds a single Packs tab that appears only when at least one pack asset is listed; with no packs installed the palette is unchanged (Forest still has 75 entries and the same tabs)
- [ ] #2 For a pack with a valid manifest.json the palette lists each name in the manifest assets list that the pack's bundle also holds; an asset the manifest lists but the bundle lacks is logged as a warning and not listed, and an asset the bundle holds but the manifest omits is not listed, matching PackCatalog.Resolve
- [ ] #3 For a pack with no manifest, or one that fails validation, every prefab in its bundle is listed (the manifest failure warning from PackPrefabs is unchanged)
- [ ] #4 Each pack entry has catalogId bundle:<pack>/<asset>, display name equal to the asset name, and stage 0; the tooltip shows the catalogId, search matches both the pack id and the name, entries are ordered by pack id then asset name, and they appear on every map
- [ ] #5 Each pack entry shows a thumbnail rendered through the existing PrefabThumbnails cache, falling back to the display name when the render fails, like other entries
- [ ] #6 Selecting a pack entry and placing it uses the existing bundle: placement path, and the saved level contains the bundle: id and the packs map
- [ ] #7 The entry-list logic is Unity-free and unit tested, written first, covering manifest-listed, manifest-absent, bundle-missing and no-pack cases, ordering, and name and pack-id search
- [ ] #8 docs/development.md (palette section) and docs/asset-bundles.md describe pack entries, their listing rules and the relaunch requirement for a newly installed pack, and the sentence saying pack assets are not listed in the palette is removed
- [ ] #9 Verified in the running game with the test pack: the Packs tab, entry, thumbnail and tooltip appear on every map the editor supports, and the entry places and saves correctly on Forest and Graveyard (and Hell if TASK-007.05.02 makes it loadable); Desert is refused by the editor
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Tests first (tests/MegabonkLevels.Tests/pack_palette_entries_tests.cs), confirm failing: manifest-listed, bundle-missing (warned, not listed), manifest-omitted (not listed), no-manifest/invalid lists all bundle assets, no packs, ordering by pack id then asset name, search by pack id and name, Pack category only when entries exist.
2. Unity-free PackPaletteEntries.Build(packIds, loadAssetNames, loadManifest) in pack_palette_entries.cs returning PaletteEntry (bundle:<pack>/<asset>, name = asset, Pack, stage 0) plus manifest-listed names missing from the bundle.
3. Add PaletteCategory.Pack; labels in PaletteGroup.Label, PaletteCategoryNames.Label/ShortLabel; treat Pack as stage-independent in PalettePick.
4. Unity side: PackPrefabs.ListAssets() enumerating UserData/LevelPacks/ via the existing catalog (no placeholders); editor_palette.cs Rebuild appends pack entries; PrefabFor routes bundle: ids to PackPrefabs.Resolve so thumbnails use PrefabThumbnails.
5. Docs: docs/development.md palette section; docs/asset-bundles.md replace the 'not listed' sentence with listing rules and relaunch requirement.
6. Verify: task check; task mod:build + relaunch; test pack on two maps (tab, entry, thumbnail, tooltip, place, save); Forest still 75 entries with no packs.
7. Commit: feat(editor): list pack assets in the palette, no attribution.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-27: tests written first (pack_palette_entries_tests.cs) and failing, then PackPaletteEntries, PaletteCategory.Pack, PackCatalog.AssetNames/ManifestOf, PackPrefabs.ListEntries and the editor_palette hookup added; 945 tests pass, mod builds. Docs updated (development.md palette section, asset-bundles.md 'Palette entries').

Forest in game: palette built 77 entries (75 + TestProp, TestModel), Packs tab shows both thumbnails, tooltip shows name / bundle:testpack/TestProp / Packs, placed TestProp (log: place 'bundle:testpack/TestProp' -> object.place), saved level has the bundle: id and packs {testpack: 1.0.0}.

Desert in game: palette shows the Packs entries with thumbnails and tooltip (bundle:testpack/TestModel), but placing does nothing: the log has 'GridShape: proceduralTiles is null' and 'could not resolve MapParameters', the kill floor never arms, and relaunch into a Desert level does not complete. Placement on Desert is blocked by the existing grid-shape resolution, not by this change. Not yet verified with no packs installed (Forest 75 / unchanged tabs).

Placement on non-Forest maps is blocked by grid-shape resolution; AC #8 now waits on subtasks TASK-007.05.01 (Desert), .02 (Hell) and .03 (Graveyard), which are dependencies of this task.

2026-10-27: Desert is a ProceduralMesh map and is refused by the editor (TASK-007.05.01); supporting it is TASK-007.06 and does not block this task. Graveyard is a Tiles map (TASK-007.05.03 verifies it). Hell fails to load with 'no MapData found' (TASK-007.05.02). AC #8 was reworded to match; the old AC #8 was removed and the reworded one is now #9, with the docs criterion at #8.
<!-- SECTION:NOTES:END -->
