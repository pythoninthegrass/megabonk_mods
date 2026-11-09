using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace MegabonkLevels;

// Walks the game's own prefab catalog (DataManager maps, StageData, SpawnInteractables, RandomObjectPlacer) for a decoded CatalogRoute.
public static class CatalogPrefabs
{
    private static MapData _lastMap;

    // DataManager.maps omits Hell and Dungeon, so scan the loaded MapData assets; the palette resolves a prefab
    // per entry, so the last hit is remembered and a destroyed MapData fails the null check and rescans.
    public static MapData TryFindMap(EMap map)
    {
        if (_lastMap != null && (int)_lastMap.eMap == (int)map)
        {
            return _lastMap;
        }

        foreach (var candidate in Resources.FindObjectsOfTypeAll<MapData>())
        {
            if (candidate != null && (int)candidate.eMap == (int)map)
            {
                _lastMap = candidate;
                return candidate;
            }
        }

        return null;
    }

    public static MapData FindMap(EMap map) =>
        TryFindMap(map) ?? throw new ArgumentException($"No MapData for map {map}.");

    // One catalog per loaded MapData, the current map first. Scene-wide channels (chests, rails, boombox,
    // charge and greed shrines) belong to the loaded scene, so only the current map's catalog carries them.
    public static IReadOnlyList<PaletteMapCatalog> DescribeAll(MapData current, SpawnInteractables interactables, RandomObjectPlacer placer)
    {
        var catalogs = new List<PaletteMapCatalog>();
        if (current != null)
        {
            catalogs.Add(Describe(current, interactables, placer));
        }

        foreach (var mapData in OtherLoadedMaps(current))
        {
            catalogs.Add(Describe(mapData, null, null));
        }

        return catalogs;
    }

    // RandomMapObject is not nameable through the interop assemblies, so its arrays are read through var.
    public static PaletteMapCatalog Describe(MapData mapData, SpawnInteractables interactables, RandomObjectPlacer placer)
    {
        var stages = new PaletteStageCatalog[mapData.stages?.Length ?? 0];
        for (var s = 0; s < stages.Length; s++)
        {
            var stage = mapData.stages[s];
            var objects = stage.randomMapObjects;
            var prefabCounts = new int[objects?.Length ?? 0];
            for (var o = 0; o < prefabCounts.Length; o++)
            {
                prefabCounts[o] = objects[o].prefabs?.Length ?? 0;
            }

            stages[s] = new PaletteStageCatalog(
                prefabCounts,
                stage.stageTilePrefabs?.flatTilePrefabs?.Length ?? 0,
                stage.stageTilePrefabs?.mapSpecificTilesPrefabs?.Length ?? 0);
        }

        var overrides = mapData.randomObjectsOverride;
        var overrideCounts = new int[overrides?.Length ?? 0];
        for (var g = 0; g < overrideCounts.Length; g++)
        {
            overrideCounts[g] = overrides[g]?.prefabs?.Length ?? 0;
        }

        return new PaletteMapCatalog(
            (EMap)(int)mapData.eMap,
            stages,
            mapData.shrines?.Length ?? 0,
            interactables?.chest != null,
            interactables?.chestFree != null,
            interactables?.rails?.Length ?? 0,
            interactables != null && EffectManager.Instance?.boomboxQuest != null,
            placer?.chargeShrineSpawns?.prefabs?.Length ?? 0,
            placer?.greedShrineSpawns?.prefabs?.Length ?? 0,
            overrideCounts);
    }

    public static GameObject Resolve(CatalogRoute route, SpawnInteractables interactables, RandomObjectPlacer placer)
    {
        switch (route.Kind)
        {
            case CatalogRouteKind.Chest:
                return interactables.chest;
            case CatalogRouteKind.ChestFree:
                return interactables.chestFree;
            case CatalogRouteKind.Boombox:
                return EffectManager.Instance.boomboxQuest;
            case CatalogRouteKind.Rail:
                return interactables.rails[route.Index];
            case CatalogRouteKind.ChargeShrine:
                return PrefabAt(placer?.chargeShrineSpawns?.prefabs, route.Index);
            case CatalogRouteKind.GreedShrine:
                return PrefabAt(placer?.greedShrineSpawns?.prefabs, route.Index);
        }

        var mapData = FindMap(route.Map);
        if (route.Kind == CatalogRouteKind.Shrine)
        {
            return mapData.shrines[route.Index];
        }

        if (route.Kind == CatalogRouteKind.RandomObjectOverride)
        {
            var groups = mapData.randomObjectsOverride;
            return groups != null && route.Index < groups.Length ? PrefabAt(groups[route.Index]?.prefabs, route.SubIndex) : null;
        }

        var stage = mapData.stages[route.Stage];
        return route.Kind switch
        {
            CatalogRouteKind.RandomMapObject => stage.randomMapObjects[route.Index].prefabs[route.SubIndex],
            CatalogRouteKind.FlatTilePrefab => stage.stageTilePrefabs.flatTilePrefabs[route.Index],
            CatalogRouteKind.SpecificTilePrefab => stage.stageTilePrefabs.mapSpecificTilesPrefabs[route.Index],
            _ => throw new ArgumentException($"Unhandled catalog route kind {route.Kind}."),
        };
    }

    private static IEnumerable<MapData> OtherLoadedMaps(MapData current)
    {
        var seen = new HashSet<int>();
        return Resources.FindObjectsOfTypeAll<MapData>()
            .Where(mapData => mapData != null && !ReferenceEquals(mapData, current) && seen.Add((int)mapData.eMap))
            .OrderBy(mapData => (int)mapData.eMap);
    }

    private static GameObject PrefabAt(GameObject[] prefabs, int index) =>
        prefabs != null && index >= 0 && index < prefabs.Length ? prefabs[index] : null;
}
