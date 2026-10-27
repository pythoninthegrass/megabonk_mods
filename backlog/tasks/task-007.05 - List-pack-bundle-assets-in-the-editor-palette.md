---
id: TASK-007.05
title: List pack bundle assets in the editor palette
status: To Do
assignee: []
created_date: '2026-10-26 23:05'
updated_date: '2026-10-27 04:48'
labels:
  - level-editor
  - assets
dependencies:
  - TASK-007.02
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
- [ ] #8 Verified in the running game with the test pack on at least two maps: the Packs tab, entry, thumbnail and tooltip appear, and the entry places and saves correctly
- [ ] #9 docs/development.md (palette section) and docs/asset-bundles.md describe pack entries, their listing rules and the relaunch requirement for a newly installed pack, and the sentence saying pack assets are not listed in the palette is removed
<!-- AC:END -->
