---
id: TASK-030
title: Give the editor palette every native map's assets plus custom pack assets
status: Done
assignee: []
created_date: '2026-11-02T04:32:00Z'
updated_date: '2026-11-03T00:36:00Z'
labels: []
dependencies: []
priority: medium
type: feature
ordinal: 137000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The palette only lists prefabs of the map the level was loaded on: CatalogPrefabs walks the loaded map's stages, shrines and interactables (docs/development.md). An author working on, say, the THPS Warehouse can only place Forest assets, even though the other kits are loaded in memory anyway (DataManager.Instance.maps[] holds every map's MapData at runtime) and pack assets surface only through the Packs tab. Expose every native map's assets (Forest, Desert, Graveyard) alongside custom pack assets so one level can mix kits — thps Warehouse pieces next to Forest tiles, Graveyard fences in any layout. Desert assets are placeable on Tiles maps even though Desert itself is a ProceduralMesh map.

The walk also misses whole interactable channels: RandomObjectPlacer carries singular RandomMapObject fields the catalog never reads (chargeShrineSpawns, greedShrineSpawns), so charge shrines are placeable nowhere and depend on the map authoring them in. The palette should list every placeable thing: all shady guy variants, chests (chest and chestFree), the Maoi, microwaves, and every shrine kind from every map plus packs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 The palette lists random objects, tiles, shrines and interactables from every native map (Forest, Desert, Graveyard), not just the loaded map's
- [x] #2 Custom pack assets remain listed and the Packs tab behaviour is unchanged
- [x] #3 A cross-map asset placed in a level persists in the file, places and edits like a native one, and renders correctly at runtime with no missing-shader artifacts
- [x] #4 Catalog build stays fast enough for editor use (no multi-second hitch when opening the palette) and each entry's map of origin is visible in the tooltip or label
- [x] #5 Verified in game: a Desert asset and a Graveyard asset are placed into a Forest level through the MCP harness, saved, reloaded and confirmed present
- [x] #6 The palette includes the singular spawn channels RandomObjectPlacer.chargeShrineSpawns and greedShrineSpawns, so charge shrines and the greed-spawn shrine are placeable regardless of map
- [x] #7 Every interactable kind is available in the palette: shady guys (all variants), chests (chest and chestFree), Maoi, microwave, and all shrine kinds (Challenge, Magnet, Cursed, Greed, Balance, Maoi, Charge)
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
Cross-map palette: walk every loaded MapData plus the singular spawn channels, keep the Packs tab as is.

## Research findings (this session)

- CatalogPrefabs.Describe walks only MapController.currentMap; PaletteCatalogBuilder turns its counts into ids and EditorPalette.Rebuild renders every entry's thumbnail up front (75 thumbnails ~0.7 s on Forest, single frame).
- Prefab names are resolved per entry through CatalogPrefabs.Resolve -> FindMap -> Resources.FindObjectsOfTypeAll<MapData>(), so one scan per entry; that must not scale with a 4x bigger catalog.
- RandomObjectPlacer (dump 332497) has randomObjects[] plus the two singular channels chargeShrineSpawns and greedShrineSpawns; only the list is walked. TASK-031 already reads both singular fields for its shrine pool (extra_shrines_patch.cs:140), so the resolution shape is proven.
- SpawnInteractables (dump 332527) exposes chest, chestFree, rails[] only; MapData exposes stages[], shrines[] and randomObjectsOverride[] (the fourth channel, currently undocumented as listable). Shady guy and the Maoi are MapData.shrines entries; the microwave's channel is not yet known from the dump (no serialized field names it) so it has to be confirmed from the running game's names.
- MapData lookup must stay Resources.FindObjectsOfTypeAll<MapData>() (DataManager.maps omits Hell and Dungeon), so Dungeon (16) and Hell (64) are loadable and placeable like the three main maps.
- Harness surface for verification is complete in run.py (load, editor, ui-tree, click-widget, save-level, state, screenshot), so a remote box is drivable over SSH; the megabonk MCP wrapper only reaches the local game dir.

## Steps

1. Tests first (tests/MegabonkLevels.Tests/): extend palette_catalog_builder_tests for the multi-map catalog (per-map order, map on every entry, charge/greed channel entries, id round-trip through CatalogRoute), catalog_route_tests for the two new kinds, palette_filter/palette_group label tests, palette_pick_tests for map preference, and new palette_thumbnails_tests for the lazy render queue (visible ids only, cached ids skipped, failed render cached, per-frame budget).
2. catalog_route.cs: add CatalogRouteKind.ChargeShrineSpawn and GreedShrineSpawn, ids interactable/chargeShrine/{i} and interactable/greedShrine/{i} (scene-level channels like chest/rails, so not map-scoped).
3. catalog_prefabs.cs: add DescribeAll(interactables, placer) returning one PaletteMapCatalog per recognized loaded MapData (current map first, then by EMap value) plus a per-catalog Dictionary<string, GameObject> of the prefabs walked, so names and thumbnails are direct lookups instead of a FindObjectsOfTypeAll per entry. Resolve gains the placer parameter for the two new kinds; keep the current-map Describe for the single-map callers.
4. palette_catalog_builder.cs: build per map (stages then shrines then interactables), carry the map on every PaletteEntry, emit the singular channel entries from the loaded placer's counts.
5. palette_entry.cs / palette_filter.cs: give PaletteEntry an EMap Map (None for pack entries) and a pure SlotLabel(EMap loaded) helper that prefixes a short map tag on cross-map entries; PaletteGroup.Label gains the map so the tooltip reads the origin (AC #4).
6. palette_pick.cs: prefer current map + current stage, then current map, then any map, so pick-block still lands on the local entry.
7. editor_palette.cs: rebuild from DescribeAll, keep pack entries appended and Packs behaviour untouched (AC #2), title shows the loaded map over the palette, tooltip carries the map, thumbnails render lazily through the new queue (visible slots + one per tab, bounded per frame) instead of one up-front loop, log per-map entry counts and the render budget outcome.
8. In-game verification: place a Desert and a Graveyard asset into a Forest level, save, reload, confirm present and rendered (shader/keyword check through the harness), confirm charge/greed shrine entries and every required interactable name in the palette listing, check the build is not a multi-second hitch (log timings).
9. Docs: docs/development.md "Catalog palette" (multi-map walk, singular channels, lazy thumbnails, tooltip/tag), docs/level-format.md catalogId table for the new shapes; then task check and a conventional commit with no attribution.

## Risks

- Thumbnail cost is the AC #4 risk: 3-5 maps times ~75 prefabs cannot render in one frame, hence the lazy queue; a page turn must stay under a frame's worth of renders.
- Cross-map prefab resolution at load time depends on the other map's MapData still being loaded; it is (TASK-007.07 relies on the same scan), but a pack-style missing shader would show up at runtime, so AC #3 checks keywords on a placed cross-map object.
- Whether the singular channels hold map-specific prefabs is unconfirmed; if the loaded placer's fields differ per map, the global id shape would resolve differently on another map. Confirmed by reading the placer's prefab names on two maps during verification.

## Open (asked the user)

- Which box runs the in-game verification: fedora over SSH, or the local wine prefix with the megabonk MCP.
- Whether MapData.randomObjectsOverride joins the walk in this task or stays out of scope.

## Decisions (user, this session)

- In-game verification runs on fedora over SSH (Proton Windows build), driven by scripts/run.py on the remote checkout; the local megabonk MCP is not the target.
- MapData.randomObjectsOverride joins the walk in this task: id shape {map}/randomObjectsOverride/{objectIndex}/{prefabIndex}, listed like a map's random objects and skipped when the array is null or empty.
<!-- SECTION:PLAN:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-11-03T00:36:00Z

---

Verified in game on the Proton build (fedora, Steam app 3405340) with the harness build `5d0032ef` / `a00516ea`.

- AC #1/#2/#6/#7 (listing): fresh launch logs `EditorPalette: built 487 entries for Forest (Forest 78, Desert 65, Graveyard 43, Dungeon 21, Hell 79, packs 201)`. Packs stayed at 201 with the Packs tab unchanged; Forest went 76 to 78 with the two new scene channels. `ui-tree` tile dumps: `Tab:Shrines` lists forest/desert/graveyard/dungeon/hell shrines, `Tab:Interactables` lists chest, chestFree, boombox, rail/0..5, chargeShrine/0, greedShrine/0, and `Tab:Overrides` lists graveyard/randomObjectsOverride/0..5/0.
- AC #7 (every kind): replaying one level that places each id logged the prefab behind it - `forest|desert|graveyard|dungeon/shrines/0..` resolve to ChallengeShrine, MagnetShrine, ShrineMaoi, ShadyGuy, CursedShrine (plus ShrineBalance at graveyard/shrines/5), `hell/shrines/0` to ShrineMaoi, `interactable/chest` to Chest, `interactable/chestFree` to ChestFree, `interactable/boombox` to BoomboxQuest, `interactable/chargeShrine/0` to ChargeShrine, `interactable/greedShrine/0` to GreedShrine, and `graveyard/randomObjectsOverride/0/0..5/0` to Microwave, PumpkinSmall, PumpkinBig, PotSmallSilver, PotBigSilver, Gravestone. A `query-objects GameObject` sweep found no other prefab named Shady/Maoi/Shrine/Chest/Greed/Charge beyond those.
- AC #3 (cross-map place, edit, render): palette clicks placed `desert/shrines/0` (ChallengeShrine) and `graveyard/randomObjectsOverride/0/0` (Microwave) into a Forest level, then `interactable/chargeShrine/0`; each logged `EditorObjectTools: place ... -> object.place`. `save-level cross-map-palette2` wrote 3 edits, a fresh process reloaded them and re-spawned the same prefabs. `material-dump` on the reloaded objects shows real MK/Toon materials with textures, `withoutTexture: 0`, and no InternalErrorShader.
- AC #4 (fast, origin visible): the same hover over a Desert tile in a Forest level added the tooltip strings `desert/shrines/0` and `Desert · Shrines`. Build cost is now logged: 191 ms on the first entry into editor mode in a session, 12-15 ms on later entries, with the 480 thumbnails drained across frames rather than in the entry frame.

---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
The editor palette now lists the assets of every native map loaded in the game plus the installed pack assets, so one level can mix kits.

**What changed**
- `CatalogPrefabs.DescribeAll` walks every recognized `MapData` (found through `Resources.FindObjectsOfTypeAll`, so Dungeon and Hell appear when loaded) and returns one `PaletteMapCatalog` per map, loaded map first. Scene-wide channels (chests, rails, boombox, charge and greed shrines) are read from the loaded scene only, so they emit once.
- Two channels the walk missed are now listed: `MapData.randomObjectsOverride` (`{map}/randomObjectsOverride/{group}/{prefab}`, grouped under a new Overrides tab) and `RandomObjectPlacer`'s singular `chargeShrineSpawns` / `greedShrineSpawns` (`interactable/chargeShrine/{i}`, `interactable/greedShrine/{i}`), with matching `CatalogRouteKind`s and resolution in `CatalogPrefabs.Resolve`.
- `PaletteEntry.Map` records the origin map (pack entries keep `EMap.None`), `PaletteGroup.LabelFor(loadedMap)` renders the `Desert · Shrines` tooltip line, and pick-block prefers an entry of the loaded map over an identically named one from another map.
- Thumbnails render lazily: `PaletteThumbnailQueue` (visible page, then the filtered set, then the catalog) drained four per frame by `EditorPalette.Tick`, replacing the one-frame loop over every entry. Only tab icons are drawn during the rebuild.
- `CatalogPrefabs.TryFindMap` memoizes the last `MapData` it resolved; the builder resolves a prefab per entry and the per-entry scan had become quadratic.

**Tests** (written before the code): new `palette_thumbnail_queue_tests.cs` (budget, cached ids skipped, failed renders cached, empty queue) plus builder tests for per-map order, the map on every entry, the override and singular-channel counts, route tests for the three new kinds, `LabelFor` tests, and pick tests for map preference. `task check` passes: 1733 xUnit, 1014 pytest, markdownlint, ruff.

**In-game verification** on the Proton build (fedora over SSH, Steam app 3405340): the build logs `built 487 entries for Forest (Forest 78, Desert 65, Graveyard 43, Dungeon 21, Hell 79, packs 201)`; packs are unchanged at 201. Palette clicks placed `desert/shrines/0` (ChallengeShrine), `graveyard/randomObjectsOverride/0/0` (Microwave) and `interactable/chargeShrine/0` (ChargeShrine) into a Forest level, `save-level` wrote the edits, and a fresh process reloaded them with the same prefabs and clean materials (`withoutTexture: 0`, no `InternalErrorShader`). Hovering a Desert tile in a Forest level added the tooltip strings `desert/shrines/0` and `Desert · Shrines`. Replaying every id in one level named the prefab behind each: ChallengeShrine, MagnetShrine, ShrineMaoi, ShadyGuy, CursedShrine, ShrineBalance, Chest, ChestFree, BoomboxQuest, ChargeShrine, GreedShrine, Microwave and the other override props, covering every interactable kind the task asked for.

**Docs**: `docs/development.md` "Catalog palette" rewritten for the multi-map walk, the singular channels, the lazy thumbnail drain and the tooltip map tag, with the measured build cost; `docs/level-format.md` catalogId table gained the three new shapes.

**Commit**: `feat(editor): list every native map's assets in the palette`, no attribution trailers.
<!-- SECTION:FINAL_SUMMARY:END -->
