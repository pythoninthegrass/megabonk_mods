using System;
using System.Collections.Generic;
using System.Linq;
using Il2Cpp;
using Il2CppAssets.Scripts.MapGeneration.ProceduralTiles;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// On A_GenerationComplete, indexes the live spawned tiles/objects by genId and, when a level file
// started the run, applies that file's edits through LiveEditPlan. See docs/runtime-map-structure.md
// for the genId scheme and where each category lives in the scene.
public static class LiveEditPatch
{
    private const string CloneSuffix = "(Clone)";
    private const string TileObjectsParentName = "TileObjectsParent";

    private static IReadOnlyList<EditOp> _pendingEdits;

    // Set by LevelLoaderPatch right before it starts a run, consumed (and cleared) by the next
    // generation so a later vanilla run is never edited.
    public static void SetPendingEdits(IReadOnlyList<EditOp> edits)
    {
        _pendingEdits = edits;
    }

    public static void Install(MelonLogger.Instance logger)
    {
        MapGenerationController.A_GenerationComplete += (Il2CppSystem.Action)(() => OnGenerationComplete(logger));
    }

    private static void OnGenerationComplete(MelonLogger.Instance logger)
    {
        var edits = _pendingEdits;
        _pendingEdits = null;

        var controller = UnityEngine.Object.FindObjectOfType<MapGenerationController>();
        if (controller == null)
        {
            return;
        }

        var index = BuildIndex(controller);
        logger.Msg($"LiveEdit: indexed {index.Count} objects: {SummarizeCategories(index)}");

        if (edits == null || edits.Count == 0)
        {
            return;
        }

        var tileGen = controller.proceduralTileGeneration;
        if (tileGen?.proceduralTiles == null)
        {
            logger.Warning("LiveEdit: map has no tile grid (not a Tiles map); edits not applied");
            return;
        }

        IReadOnlyList<LiveAction> plan;
        try
        {
            plan = LiveEditPlan.Build(edits);
        }
        catch (ArgumentException ex)
        {
            logger.Error($"LiveEdit: invalid edit list: {ex.Message}");
            return;
        }

        var applier = new Applier(logger, controller, index);
        foreach (var action in plan)
        {
            try
            {
                applier.Apply(action);
            }
            catch (Exception ex)
            {
                logger.Error($"LiveEdit: {action.Kind} failed: {ex}");
            }
        }

        logger.Msg($"LiveEdit: applied {plan.Count} edit(s)");
    }

    private static Dictionary<string, GameObject> BuildIndex(MapGenerationController controller)
    {
        var sources = new Dictionary<string, IReadOnlyList<GameObject>>();
        var tileGen = controller.proceduralTileGeneration;
        sources["tile"] = ToList(tileGen?.tiles);
        sources["flatTile"] = ToList(tileGen?.flatTiles);
        sources["fillTile"] = ToList(tileGen?.fillTiles);
        sources["tileObject"] = Children(controller.RandomTileObjects?.tileObjectsParent?.transform);

        // Random objects, chests, shrines, pots, rails etc. are all instantiated as scene roots named
        // "<prefab>(Clone)", after the TileObjectsParent root; root order is spawn order.
        var spawned = new Dictionary<string, List<GameObject>>();
        var seenTileObjectsParent = false;
        foreach (var root in controller.gameObject.scene.GetRootGameObjects())
        {
            if (root.name == TileObjectsParentName)
            {
                seenTileObjectsParent = true;
                continue;
            }

            if (!seenTileObjectsParent || !root.name.EndsWith(CloneSuffix, StringComparison.Ordinal))
            {
                continue;
            }

            var category = "object:" + root.name.Substring(0, root.name.Length - CloneSuffix.Length);
            if (!spawned.TryGetValue(category, out var list))
            {
                spawned[category] = list = new List<GameObject>();
            }

            list.Add(root);
        }

        foreach (var (category, list) in spawned)
        {
            sources[category] = list;
        }

        return GenIdAssigner.Index(sources);
    }

    private static string SummarizeCategories(Dictionary<string, GameObject> index) =>
        string.Join(", ", index.Keys
            .GroupBy(k => k.Substring(0, k.LastIndexOf(':')))
            .Select(g => $"{g.Key}x{g.Count()}"));

    private static IReadOnlyList<GameObject> ToList(Il2CppSystem.Collections.Generic.List<GameObject> source)
    {
        var result = new List<GameObject>();
        for (var i = 0; source != null && i < source.Count; i++)
        {
            result.Add(source[i]);
        }

        return result;
    }

    private static IReadOnlyList<GameObject> Children(Transform parent)
    {
        var result = new List<GameObject>();
        for (var i = 0; parent != null && i < parent.childCount; i++)
        {
            result.Add(parent.GetChild(i).gameObject);
        }

        return result;
    }

    private sealed class Applier
    {
        private readonly MelonLogger.Instance _logger;
        private readonly MapGenerationController _controller;
        private readonly ProceduralTileGeneration _tileGen;
        private readonly MapParameters _mapParameters;
        private readonly Dictionary<string, GameObject> _index;
        private readonly Dictionary<int, GameObject> _placed = new();

        public Applier(MelonLogger.Instance logger, MapGenerationController controller, Dictionary<string, GameObject> index)
        {
            _logger = logger;
            _controller = controller;
            _tileGen = controller.proceduralTileGeneration;
            _mapParameters = _tileGen.currentMapParameters ?? _tileGen.currentStage?.mapParameters;
            _index = index;
        }

        public void Apply(LiveAction action)
        {
            switch (action.Kind)
            {
                case LiveActionKind.SetTile:
                    SetTile(action);
                    break;
                case LiveActionKind.RemoveTile:
                    RemoveTile(action);
                    break;
                case LiveActionKind.SpawnObject:
                    SpawnObject(action);
                    break;
                case LiveActionKind.MoveObject:
                    MoveObject(action);
                    break;
                case LiveActionKind.RemoveObject:
                    RemoveObject(action);
                    break;
            }
        }

        private ProceduralTile TileAt(int x, int z)
        {
            var grid = _tileGen.proceduralTiles;
            return x < grid.Length && grid[x] != null && z < grid[x].Length ? grid[x][z] : null;
        }

        private void SetTile(LiveAction action)
        {
            var tile = TileAt(action.X, action.Z);
            var state = action.Tile.Value;
            if (tile == null)
            {
                _logger.Warning($"LiveEdit: no live tile at ({action.X},{action.Z}); adding tiles is not supported yet");
                return;
            }

            var before = tile.transform.position;
            var y = state.Height * _mapParameters.scaledTileHeight;
            tile.transform.position = new Vector3(before.x, y, before.z);
            tile.posY = state.Height;
            _logger.Msg($"LiveEdit: tile ({action.X},{action.Z}) height {before.y} -> {y} (level {state.Height})");

            if (state.Slope != SlopeDirection.None)
            {
                _logger.Warning($"LiveEdit: tile ({action.X},{action.Z}) slope {state.Slope} not applied; slope edits are not supported yet");
            }
        }

        private void RemoveTile(LiveAction action)
        {
            var tile = TileAt(action.X, action.Z);
            if (tile == null)
            {
                _logger.Warning($"LiveEdit: no live tile at ({action.X},{action.Z}) to remove");
                return;
            }

            UnityEngine.Object.Destroy(tile.gameObject);
            _tileGen.proceduralTiles[action.X][action.Z] = null;
            _logger.Msg($"LiveEdit: removed tile ({action.X},{action.Z})");
        }

        private void SpawnObject(LiveAction action)
        {
            var prefab = ResolvePrefab(CatalogRoute.Parse(CatalogId.Parse(action.CatalogId)));
            var t = action.Transform.Value;
            var spawned = UnityEngine.Object.Instantiate(prefab, ToVector(t.Position), Quaternion.Euler(ToVector(t.Rotation)));
            spawned.transform.localScale = ToVector(t.Scale);
            _placed[action.Target.PlacementId] = spawned;
            _logger.Msg($"LiveEdit: spawned '{action.CatalogId}' (prefab '{prefab.name}') as placement:{action.Target.PlacementId} at {spawned.transform.position}");
        }

        private void MoveObject(LiveAction action)
        {
            var go = Resolve(action.Target);
            if (go == null)
            {
                return;
            }

            var t = action.Transform.Value;
            go.transform.position = ToVector(t.Position);
            go.transform.rotation = Quaternion.Euler(ToVector(t.Rotation));
            go.transform.localScale = ToVector(t.Scale);
            _logger.Msg($"LiveEdit: moved {action.Target.Serialize()} '{go.name}' to {go.transform.position}");
        }

        private void RemoveObject(LiveAction action)
        {
            var go = Resolve(action.Target);
            if (go == null)
            {
                return;
            }

            var name = go.name;
            UnityEngine.Object.Destroy(go);
            _logger.Msg($"LiveEdit: removed {action.Target.Serialize()} '{name}'");
        }

        private GameObject Resolve(ObjectTarget target)
        {
            var found = target.Kind == ObjectTargetKind.GenId
                ? _index.GetValueOrDefault(target.GenId)
                : _placed.GetValueOrDefault(target.PlacementId);
            if (found == null)
            {
                _logger.Warning($"LiveEdit: no live object for {target.Serialize()}");
            }

            return found;
        }

        private GameObject ResolvePrefab(CatalogRoute route)
        {
            switch (route.Kind)
            {
                case CatalogRouteKind.Chest:
                    return _controller.interactablesSpawner.chest;
                case CatalogRouteKind.ChestFree:
                    return _controller.interactablesSpawner.chestFree;
                case CatalogRouteKind.Rail:
                    return _controller.interactablesSpawner.rails[route.Index];
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

        private static MapData FindMap(EMap map)
        {
            var maps = DataManager.Instance.maps;
            for (var i = 0; i < maps.Count; i++)
            {
                if ((int)maps[i].eMap == (int)map)
                {
                    return maps[i];
                }
            }

            throw new ArgumentException($"No MapData for map {map}.");
        }

        private static Vector3 ToVector(Vector3Data v) => new(v.X, v.Y, v.Z);
    }
}
