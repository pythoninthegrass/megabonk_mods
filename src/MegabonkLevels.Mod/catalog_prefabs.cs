using System;
using Il2Cpp;
using UnityEngine;

namespace MegabonkLevels;

// Walks the game's own prefab catalog (DataManager maps, StageData, SpawnInteractables) for a decoded CatalogRoute.
public static class CatalogPrefabs
{
    public static GameObject Resolve(CatalogRoute route, SpawnInteractables interactables)
    {
        switch (route.Kind)
        {
            case CatalogRouteKind.Chest:
                return interactables.chest;
            case CatalogRouteKind.ChestFree:
                return interactables.chestFree;
            case CatalogRouteKind.Rail:
                return interactables.rails[route.Index];
        }

        var mapData = FindMap(route.Map);
        if (route.Kind == CatalogRouteKind.Shrine)
        {
            return mapData.shrines[route.Index];
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

    // DataManager.maps omits Hell and Dungeon, so look maps up through the loaded MapData assets.
    public static MapData TryFindMap(EMap map)
    {
        foreach (var candidate in Resources.FindObjectsOfTypeAll<MapData>())
        {
            if ((int)candidate.eMap == (int)map)
            {
                return candidate;
            }
        }

        return null;
    }

    public static MapData FindMap(EMap map) =>
        TryFindMap(map) ?? throw new ArgumentException($"No MapData for map {map}.");

    public static PaletteMapCatalog Describe(MapData mapData, SpawnInteractables interactables)
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

        return new PaletteMapCatalog(
            (EMap)(int)mapData.eMap,
            stages,
            mapData.shrines?.Length ?? 0,
            interactables?.chest != null,
            interactables?.chestFree != null,
            interactables?.rails?.Length ?? 0);
    }
}
