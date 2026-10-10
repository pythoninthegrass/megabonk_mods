using System;
using System.Collections.Generic;
using System.Linq;
using Il2Cpp;
using Il2CppAssets.Scripts.MapGeneration.ProceduralTiles;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// LowestLevel is the lowest tile level the generator produced, the floor for the editor's Lower tool.
public readonly record struct LiveGrid(int Width, int Depth, float Spacing, float TileHeight, int LowestLevel);

// On A_GenerationComplete, indexes the live spawned tiles/objects by genId and, when a level file
// started the run, applies that file's edits through LiveEditPlan. See docs/runtime-map-structure.md
// for the genId scheme and where each category lives in the scene.
public static class LiveEditPatch
{
    private const string CloneSuffix = "(Clone)";
    private const string TileObjectsParentName = "TileObjectsParent";

    private static IReadOnlyList<EditOp> _pendingEdits;
    private static Session _session;

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

    public static LiveGrid? Grid => _session?.Grid;

    // The tile's current state: the generated grid with every applied edit on top, null for an empty cell.
    public static TileState? TileAt(int x, int z) => _session?.Planner.State.GetTile(x, z);

    // The baked ground collision, replaced after every terrain edit.
    public static MeshCollider GroundCollider() => _session?.TileGen.collider?.GetComponent<MeshCollider>();

    // Applies one edit to the running level the same way a level file's edits are applied at load.
    public static bool ApplyLive(EditOp op)
    {
        var session = _session;
        if (session == null)
        {
            return false;
        }

        LiveAction action;
        try
        {
            action = session.Planner.Apply(op);
        }
        catch (ArgumentException ex)
        {
            session.Logger.Error($"LiveEdit: invalid edit {op.OpType}: {ex.Message}");
            return false;
        }

        var plan = new[] { action };
        ApplyPlan(session, plan);
        return true;
    }

    private static void OnGenerationComplete(MelonLogger.Instance logger)
    {
        var edits = _pendingEdits;
        _pendingEdits = null;
        _session = null;

        var controller = UnityEngine.Object.FindObjectOfType<MapGenerationController>();
        if (controller == null)
        {
            return;
        }

        var index = BuildIndex(controller);
        logger.Msg($"LiveEdit: indexed {index.Count} objects: {SummarizeCategories(index)}");

        var tileGen = controller.proceduralTileGeneration;
        if (tileGen?.proceduralTiles == null)
        {
            if (edits != null && edits.Count > 0)
            {
                logger.Warning("LiveEdit: map has no tile grid (not a Tiles map); edits not applied");
            }

            KillFloorWatcher.Disarm();
            return;
        }

        var baseline = SnapshotGrid(tileGen);
        var session = new Session(logger, controller, index, baseline);
        if (edits != null && edits.Count > 0)
        {
            ApplyEdits(session, baseline, edits);
        }

        _session = session;
        if (edits == null)
        {
            KillFloorWatcher.Disarm();
            return;
        }

        KillFloorWatcher.Arm(tileGen, logger);
    }

    private static void ApplyEdits(Session session, LevelState baseline, IReadOnlyList<EditOp> edits)
    {
        IReadOnlyList<LiveAction> plan;
        try
        {
            plan = LiveEditPlan.Build(edits, baseline);
        }
        catch (ArgumentException ex)
        {
            session.Logger.Error($"LiveEdit: invalid edit list: {ex.Message}");
            return;
        }

        foreach (var op in edits)
        {
            session.Planner.Apply(op);
        }

        ApplyPlan(session, plan);
    }

    private static void ApplyPlan(Session session, IReadOnlyList<LiveAction> plan)
    {
        foreach (var action in plan)
        {
            try
            {
                session.Applier.Apply(action);
            }
            catch (Exception ex)
            {
                session.Logger.Error($"LiveEdit: {action.Kind} failed: {ex}");
            }
        }

        session.Logger.Msg($"LiveEdit: applied {plan.Count} edit(s)");

        if (LiveEditPlan.ChangesTerrain(plan))
        {
            var touched = plan.Where(a => a.Kind == LiveActionKind.SetTile).Select(a => (a.X, a.Z));
            FillRegeneration.Regenerate(session.TileGen, session.Grid.Spacing, touched, session.Logger);
            CollisionRebuild.Replace(session.TileGen, session.Logger);
        }
    }

    // The generated grid before any edit, read from the live tiles.
    private static LevelState SnapshotGrid(ProceduralTileGeneration tileGen)
    {
        var tiles = new Dictionary<(int X, int Z), TileState>();
        var grid = tileGen.proceduralTiles;
        for (var x = 0; x < grid.Length; x++)
        {
            for (var z = 0; grid[x] != null && z < grid[x].Length; z++)
            {
                var tile = grid[x][z];
                if (tile != null)
                {
                    tiles[(x, z)] = new TileState(tile.posY, SlopeOf(tile));
                }
            }
        }

        return LevelState.FromTiles(tiles);
    }

    private static SlopeDirection SlopeOf(ProceduralTile tile) =>
        tile == null || tile.isFlat
            ? SlopeDirection.None
            : TilePlacement.SlopeFromVector(Mathf.RoundToInt(tile.dir.x), Mathf.RoundToInt(tile.dir.z));

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

    // Everything needed to keep editing the level generated last: the planner holds the generated grid plus every edit.
    private sealed class Session
    {
        public readonly MelonLogger.Instance Logger;
        public readonly ProceduralTileGeneration TileGen;
        public readonly LiveGrid Grid;
        public readonly Applier Applier;
        public readonly LiveEditPlanner Planner;

        public Session(MelonLogger.Instance logger, MapGenerationController controller, Dictionary<string, GameObject> index, LevelState baseline)
        {
            Logger = logger;
            TileGen = controller.proceduralTileGeneration;
            var columns = TileGen.proceduralTiles;
            var mapParameters = TileGen.currentMapParameters ?? TileGen.currentStage?.mapParameters;
            var lowestLevel = baseline.Tiles.Count == 0 ? 0 : baseline.Tiles.Values.Min(t => t.Height);
            Grid = new LiveGrid(columns.Length, columns[0].Length, mapParameters.scaledTileWidth, mapParameters.scaledTileHeight, lowestLevel);
            Applier = new Applier(logger, controller, index);
            Planner = new LiveEditPlanner(baseline);
        }
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

        private bool InGrid(int x, int z)
        {
            var grid = _tileGen.proceduralTiles;
            return x >= 0 && x < grid.Length && grid[x] != null && z >= 0 && z < grid[x].Length;
        }

        private void SetTile(LiveAction action)
        {
            var (x, z) = (action.X, action.Z);
            if (!InGrid(x, z))
            {
                _logger.Warning($"LiveEdit: ({x},{z}) is outside the {_tileGen.proceduralTiles.Length}-wide tile grid; adding tiles beyond the grid is not supported");
                return;
            }

            var state = action.Tile.Value;
            var live = TileAt(x, z);
            var kind = TilePlacement.Decide(live != null, SlopeOf(live), state);

            if (kind == TilePlacementKind.MoveOnly)
            {
                var before = live.transform.position;
                var y = state.Height * _mapParameters.scaledTileHeight;
                live.transform.position = new Vector3(before.x, y, before.z);
                live.posY = state.Height;
                _logger.Msg($"LiveEdit: tile ({x},{z}) height {before.y} -> {y} (level {state.Height})");
                return;
            }

            var slope = kind is TilePlacementKind.AddSlope or TilePlacementKind.ReplaceWithSlope;
            var direction = slope
                ? ToDirection(TilePlacement.UphillVector(state.Slope))
                : live != null ? live.dir : Vector3.forward;
            var prefab = slope ? _tileGen.slopeTile : _tileGen.flatTile;
            var created = _tileGen.InstantiateTile(new Vector2Int(x, z), state.Height, prefab, direction, direction);
            var tile = created.GetComponent<ProceduralTile>();

            if (live != null)
            {
                _tileGen.tiles.Remove(live.gameObject);
                _tileGen.flatTiles.Remove(live.gameObject);
                live.gameObject.SetActive(false);
                UnityEngine.Object.Destroy(live.gameObject);
            }

            if (!_tileGen.tiles.Contains(created))
            {
                _tileGen.tiles.Add(created);
            }

            _tileGen.proceduralTiles[x][z] = tile;
            _logger.Msg($"LiveEdit: {kind} at ({x},{z}) prefab '{prefab.name}' level {state.Height} slope {state.Slope} -> {created.transform.position} euler {created.transform.eulerAngles}");
        }

        private static Vector3 ToDirection((int Dx, int Dz) step) => new(step.Dx, 0, step.Dz);

        private void RemoveTile(LiveAction action)
        {
            var tile = TileAt(action.X, action.Z);
            if (tile == null)
            {
                _logger.Warning($"LiveEdit: no live tile at ({action.X},{action.Z}) to remove");
                return;
            }

            _tileGen.tiles.Remove(tile.gameObject);
            _tileGen.flatTiles.Remove(tile.gameObject);
            tile.gameObject.SetActive(false);
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

        private GameObject ResolvePrefab(CatalogRoute route) =>
            CatalogPrefabs.Resolve(route, _controller.interactablesSpawner);

        private static Vector3 ToVector(Vector3Data v) => new(v.X, v.Y, v.Z);
    }
}
