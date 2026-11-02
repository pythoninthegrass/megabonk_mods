---
id: TASK-030
title: Give the editor palette every native map's assets plus custom pack assets
status: To Do
assignee: []
created_date: '2026-11-02T04:32:00Z'
updated_date: '2026-11-02T04:40:00Z'
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
- [ ] #1 The palette lists random objects, tiles, shrines and interactables from every native map (Forest, Desert, Graveyard), not just the loaded map's
- [ ] #2 Custom pack assets remain listed and the Packs tab behaviour is unchanged
- [ ] #3 A cross-map asset placed in a level persists in the file, places and edits like a native one, and renders correctly at runtime with no missing-shader artifacts
- [ ] #4 Catalog build stays fast enough for editor use (no multi-second hitch when opening the palette) and each entry's map of origin is visible in the tooltip or label
- [ ] #5 Verified in game: a Desert asset and a Graveyard asset are placed into a Forest level through the MCP harness, saved, reloaded and confirmed present
- [ ] #6 The palette includes the singular spawn channels RandomObjectPlacer.chargeShrineSpawns and greedShrineSpawns, so charge shrines and the greed-spawn shrine are placeable regardless of map
- [ ] #7 Every interactable kind is available in the palette: shady guys (all variants), chests (chest and chestFree), Maoi, microwave, and all shrine kinds (Challenge, Magnet, Cursed, Greed, Balance, Maoi, Charge)
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [ ] #1 task check passes
- [ ] #2 Tests written first for testable logic
- [ ] #3 Docs updated
- [ ] #4 Conventional commit with no attribution
<!-- DOD:END -->
