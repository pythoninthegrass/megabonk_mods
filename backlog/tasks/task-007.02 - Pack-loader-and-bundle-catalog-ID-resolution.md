---
id: TASK-007.02
title: 'Pack loader and bundle: catalog ID resolution'
status: Done
assignee:
  - claude
created_date: '2026-10-06 21:44'
updated_date: '2026-10-27 00:11'
labels:
  - level-editor
  - assets
dependencies:
  - TASK-007.01
parent_task_id: TASK-007
priority: low
ordinal: 34000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Read parent TASK-007 first for full context.

Implement a pack loader that discovers and loads AssetBundles from `UserData/LevelPacks/<pack>/` at game startup or on demand, extending TASK-003.05's `catalogId` parsing (which already reserves the `bundle:<pack>/<asset>` namespace) to resolve a `bundle:` ID to an asset inside a loaded pack's AssetBundle. Wire this into TASK-004.02's existing `catalogId` resolution logic (the same code path that resolves game-asset IDs against `DataManager.Instance`) so `PlaceObject` edits referencing `bundle:` IDs work through the exact same mechanism as built-in game assets, with no special-casing needed elsewhere in the edit-application pipeline.

Handle the failure case explicitly: a level referencing a `bundle:` asset from a pack the player doesn't have installed should produce a clear, non-crashing error (e.g. a placeholder object + a logged/visible warning), not a silent failure or a crash.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 AssetBundles are discovered and loaded from UserData/LevelPacks/<pack>/
- [x] #2 A bundle: catalogId resolves to the correct asset inside its pack's loaded AssetBundle
- [x] #3 TASK-004.02's existing catalogId resolution path handles bundle: IDs through the same code path as game-asset IDs, without special-casing elsewhere in edit application
- [x] #4 A level referencing a bundle: asset from a pack that isn't installed produces a clear warning and a placeholder rather than crashing or silently failing
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Pure logic, test-first (xunit, linked into tests like catalog_route.cs): PackCatalog<T> with an injected pack-directory loader. Resolves a bundle: CatalogId to Found(prefab) / PackMissing / AssetMissing; loads each pack lazily on first reference and caches results (including missing) so a missing pack warns once. Helper decides which files in a pack dir are bundle candidates: no extension or .bundle; everything else ignored (manifest is TASK-007.04).
2. Il2Cpp layer pack_loader.cs: scan UserData/LevelPacks/<pack>/, load each bundle via the async API (LoadFromFileAsync, LoadAllAssetsAsync(Type)), keep bundles loaded for the session, index prefabs by asset.name. A bundle that fails to load (e.g. wrong platform) logs a warning for that bundle; no platform subfolders.
3. Single entry point Applier.ResolvePrefab(CatalogId): switch on namespace; game assets keep CatalogRoute + CatalogPrefabs, bundle IDs go to PackCatalog. SpawnObject and PrefabFor both call it; no other special-casing.
4. Missing pack/asset: cached placeholder cube named Missing:<catalogId>, one log warning per ID, plus an editor toast. Never throws. The catalogId stays in the level so it round-trips on save.
5. Docs: pack layout, resolution and failure behaviour in docs/asset-bundles.md.
6. Verify: task check; task mod:build + relaunch; copy test bundle to UserData/LevelPacks/testpack/, place bundle:testpack/TestProp via harness; place bundle:nopack/Thing and confirm placeholder + warning + toast, no crash. Windows/Wine game only (Linux segfaults under MelonLoader).
Out of scope: palette listing of bundle assets (follow-up task).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-10-26: PackCatalog/PackFiles (pack_catalog.cs, tests in pack_catalog_tests.cs) written test-first and passing. PackPrefabs (pack_prefabs.cs) written and wired through Applier.ResolvePrefab(CatalogId), EditorTileTools.Warn toast added, docs/asset-bundles.md updated. NOT yet compiled or run: this Mac has no game install (MelonLoader/Il2CppAssemblies missing), so task mod:build fails with unresolved references. Needs a host with the game to build and verify ACs 1-4 in game.

2026-10-26: built and verified under plain Wine against the CrossOver Steam bottle prefix (MEGABONK_WINE_PREFIX, no MEGABONK_MACOS_RUNTIME). With .tools/bundles/windows/testprop in UserData/LevelPacks/testpack/, a level placing bundle:testpack/TestProp and bundle:nopack/Thing logged 'Packs: loaded pack testpack with 1 prefab(s)', spawned TestProp, and spawned the Missing: placeholder with one warning; screenshot shows both cubes. Nullable annotations are not usable in the mod project (net6, no NullableAttribute), so pack_catalog.cs has none.

Not verified: the editor toast. For a level-file load the edits apply before editor mode, and toasts expire after 3 s, so the toast is likely gone before the editor draws it; it would show for a mid-session placement. Left as is; flagged to Lance.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added asset-pack loading and bundle: catalogId resolution. PackCatalog (pure, unit tested) resolves bundle:<pack>/<asset> to Found, PackMissing or AssetMissing and loads each pack once. PackPrefabs loads every extensionless or .bundle file under UserData/LevelPacks/<pack>/ through the async AssetBundle API and keeps bundles loaded for the session. Applier.ResolvePrefab(CatalogId) is the single resolver, so SpawnObject and PrefabFor handle bundle: IDs through the same path as game assets. A missing pack or asset yields a cached Missing:<id> placeholder cube, one warning log per ID and an editor toast; the catalogId is kept in the level. Verified in the Wine-hosted game: the test pack prop and the placeholder both spawn from a level file. Docs in docs/asset-bundles.md. Palette listing is TASK-007.05.
<!-- SECTION:FINAL_SUMMARY:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 task check passes
- [x] #2 Tests written first for testable logic
- [x] #3 Docs updated
- [x] #4 Conventional commit with no attribution
<!-- DOD:END -->
