using System.Collections.Generic;
using System.Linq;
using Il2Cpp;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Runtime pass that spawns the level's extra shrines after map generation, at probed spots that
// keep a shrine's charge sphere off other objects, other shrines, and the routes between the
// spawn portal, the boss portal and the final portal.
public static class ExtraShrinesPatch
{
    private const int CandidateBudget = 256;

    private static readonly List<GameObject> _spawned = new();

    // Extras belong to the run that spawned them; a fresh generation must never see the old ones.
    public static void ClearStale()
    {
        foreach (var go in _spawned)
        {
            if (go != null) UnityEngine.Object.Destroy(go);
        }

        _spawned.Clear();
    }

    public static void Spawn(LevelFile settings, IReadOnlyDictionary<string, GameObject> index, LevelState state,
        ProceduralTileGeneration tiles, MeshCollider ground, MapGenerationController controller, MelonLogger.Instance logger)
    {
        if (!ExtraShrines.Enabled(settings)) return;
        if (tiles == null || ground == null || state.Tiles.Count == 0)
        {
            logger.Warning("ExtraShrines: no tile ground available; no extra shrines spawned");
            return;
        }

        var allowed = AllowedKindsFromSettings(settings, logger);
        if (ReferenceEquals(allowed, s_skipPass)) return;

        var pool = BuildPool(settings, controller, allowed, logger);
        if (pool.Count == 0) return;

        Physics.SyncTransforms();
        var start = settings.PlayerStart is { Count: 3 }
            ? new Vector3(settings.PlayerStart[0], settings.PlayerStart[1], settings.PlayerStart[2])
            : MapGenerationController.tileSpawnPosition;
        var points = PlacementProbe.ReachablePoints(state, tiles, ground, start, logger, "ExtraShrines").Values.ToList();
        var (anchors, routes) = HotPathGeometry(controller, start);
        var existing = ExistingShrinePositions(index);
        var random = new System.Random(System.Guid.NewGuid().GetHashCode());
        var spacing = tiles.currentMapParameters.scaledTileWidth / PlacementProbe.SamplesPerTile;
        var requested = settings.ExtraShrines;
        var spawned = 0;

        for (var n = 0; n < requested; n++)
        {
            var entry = pool[random.Next(pool.Count)];
            var placed = false;
            Vector3 position = default;
            float nearestShrine = 0f, nearestRoute = 0f;
            if (!InteractableRandomization.TryChoose(points, random.Next, candidate =>
                {
                    var jitter = candidate + new Vector3((float)(random.NextDouble() - 0.5) * spacing * 0.5f, 0,
                        (float)(random.NextDouble() - 0.5) * spacing * 0.5f);
                    if (!PlacementProbe.Surface(ground, jitter, out var floor, false)) return false;
                    var point = new Vector3Data(floor.x, floor.y, floor.z);
                    if (!ExtraShrines.HotPathClear(point, anchors, routes, ExtraShrines.ChargeZoneReach)) return false;
                    if (!ExtraShrines.ShrineClear(point, existing, ExtraShrines.ChargeZoneReach)) return false;

                    var trial = CreateTrial(entry, floor);
                    if (trial == null) return false;
                    Physics.SyncTransforms();
                    if (!PlacementProbe.TryBounds(trial, out var bounds)
                        || !PlacementProbe.Supported(ground, ShiftedDown(bounds, floor.y), floor.y)
                        || !PlacementProbe.Unoccupied(ShiftedDown(bounds, floor.y), floor.y, trial.transform)
                        || PlacementProbe.OverlapsObjects(ShiftedDown(bounds, floor.y), trial, index, _spawned))
                    {
                        UnityEngine.Object.Destroy(trial);
                        return false;
                    }

                    trial.transform.position += Vector3.up * (floor.y - bounds.min.y);
                    Physics.SyncTransforms();
                    _spawned.Add(trial);
                    position = trial.transform.position;
                    nearestShrine = Nearest(point, existing);
                    nearestRoute = NearestRoute(point, routes);
                    existing.Add(point);
                    placed = true;
                    return true;
                }, CandidateBudget, out _))
            {
                logger.Warning($"ExtraShrines: no safe spot found for a {entry.Kind} shrine (attempt {n + 1}/{requested})");
                continue;
            }

            if (placed)
            {
                spawned++;
                logger.Msg($"ExtraShrines: spawned {entry.Kind} at {position.ToString("F3")} nearestShrine={nearestShrine:F1} nearestRoute={nearestRoute:F1}");
            }
        }

        logger.Msg($"ExtraShrines: spawned={spawned} requested={requested} pool={pool.Count} reachableFlatSamples={points.Count}");
    }

    private static readonly IReadOnlySet<ExtraShrineKind> s_skipPass = new HashSet<ExtraShrineKind>();

    // null means the full pool; the sentinel reference means names were given but none were valid.
    private static IReadOnlySet<ExtraShrineKind> AllowedKindsFromSettings(LevelFile settings, MelonLogger.Instance logger)
    {
        var names = settings.ExtraShrineKinds;
        if (names == null || names.Count == 0) return null;
        var valid = names.Where(ExtraShrines.IsKnownKind).Distinct().ToList();
        foreach (var bad in names.Where(name => !string.IsNullOrEmpty(name) && !ExtraShrines.IsKnownKind(name)))
        {
            logger.Warning($"ExtraShrines: unknown shrine kind '{bad}' ignored");
        }

        if (valid.Count == 0)
        {
            logger.Warning("ExtraShrines: no valid shrine kinds configured; no extra shrines spawned");
            return s_skipPass;
        }

        return ExtraShrines.AllowedKinds(valid);
    }

    private readonly record struct PoolEntry(ExtraShrineKind Kind, GameObject Prefab, GameObject LiveClone);

    // The map's own shrine prefabs plus the dedicated charge and greed channels on the object placer.
    private static List<PoolEntry> BuildPool(LevelFile settings, MapGenerationController controller,
        IReadOnlySet<ExtraShrineKind> allowed, MelonLogger.Instance logger)
    {
        var prefabs = new List<GameObject>();
        var mapData = CatalogPrefabs.TryFindMap(settings.Map);
        if (mapData?.shrines != null) prefabs.AddRange(mapData.shrines.Where(p => p != null));
        var placer = controller.randomObjectPlacer;
        foreach (var channel in new[] { placer?.chargeShrineSpawns, placer?.greedShrineSpawns })
        {
            if (channel?.prefabs != null) prefabs.AddRange(channel.prefabs.Where(p => p != null));
        }

        var live = SceneShrines().ToList();
        var pool = new List<PoolEntry>();
        foreach (var prefab in prefabs)
        {
            var kind = Kind(prefab);
            if (kind == null || (allowed != null && !allowed.Contains(kind.Value))) continue;
            pool.Add(new PoolEntry(kind.Value, prefab, live.FirstOrDefault(go => Kind(go) == kind)));
        }

        if (pool.Count == 0)
        {
            var kinds = allowed == null ? "any" : string.Join(",", allowed);
            logger.Warning($"ExtraShrines: no shrine prefabs available for kinds [{kinds}]; no extra shrines spawned");
        }

        return pool;
    }

    private static IEnumerable<GameObject> SceneShrines()
    {
        foreach (var go in UnityEngine.Object.FindObjectsOfType<GameObject>())
        {
            if (go != null && go.activeInHierarchy && go.GetComponentInChildren<Collider>() != null && Kind(go) != null) yield return go;
        }
    }

    // Cloning a live shrine preserves its authored pivot and upright rotation; prefabs get the
    // native-up correction (Moai models are authored Z-up, the rest Y-up).
    private static GameObject CreateTrial(PoolEntry entry, Vector3 floor)
    {
        if (entry.LiveClone != null) return UnityEngine.Object.Instantiate(entry.LiveClone, floor, entry.LiveClone.transform.rotation);
        var axis = entry.Kind == ExtraShrineKind.Moai ? new Vector3(0, 0, 1) : Vector3.up;
        var rotation = entry.Prefab.transform.rotation;
        var upright = Quaternion.FromToRotation(rotation * axis, Vector3.up) * rotation;
        return UnityEngine.Object.Instantiate(entry.Prefab, floor, upright);
    }

    private static Bounds ShiftedDown(Bounds bounds, float floorY) =>
        new(bounds.center + Vector3.up * (floorY - bounds.min.y), bounds.size);

    private static List<Vector3Data> ExistingShrinePositions(IReadOnlyDictionary<string, GameObject> index)
    {
        var positions = new List<Vector3Data>();
        var objects = index.Values.Where(go => go != null && go.activeInHierarchy && Kind(go) != null)
            .Concat(LiveEditPatch.PickableObjects().Where(pair => pair.Object != null).Select(pair => pair.Object).Where(go => Kind(go) != null));
        foreach (var go in objects)
        {
            var p = go.transform.position;
            positions.Add(new Vector3Data(p.x, p.y, p.z));
        }

        return positions;
    }

    private static (List<Vector3Data> Anchors, List<(Vector3Data From, Vector3Data To)> Routes) HotPathGeometry(
        MapGenerationController controller, Vector3 start)
    {
        Vector3Data? Position(GameObject go) => go != null ? ToData(go.transform.position) : null;
        var anchors = new[] { controller.spawnPortal, controller.spawnPlatform, controller.bossPortal, controller.bossPortalFinal, controller.graveyardBossPortal }
            .Select(Position).Where(a => a != null).Select(a => a.Value).ToList();
        anchors.Add(ToData(start));
        var routes = new List<(Vector3Data, Vector3Data)>();
        var spawn = Position(controller.spawnPortal);
        var boss = Position(controller.bossPortal);
        var final = Position(controller.bossPortalFinal);
        if (spawn != null && boss != null) routes.Add((spawn.Value, boss.Value));
        if (boss != null && final != null) routes.Add((boss.Value, final.Value));
        return (anchors, routes);
    }

    private static Vector3Data ToData(Vector3 v) => new(v.x, v.y, v.z);

    private static float Nearest(Vector3Data point, IReadOnlyList<Vector3Data> points) =>
        points.Count == 0 ? float.PositiveInfinity : points.Min(other => ExtraShrines.Distance(point, other));

    private static float NearestRoute(Vector3Data point, IReadOnlyList<(Vector3Data From, Vector3Data To)> routes) =>
        routes.Count == 0 ? float.PositiveInfinity : routes.Min(route => ExtraShrines.SegmentDistance(point, route.From, route.To));

    private static ExtraShrineKind? Kind(GameObject go)
    {
        if (go.GetComponentInChildren<InteractableShrineChallenge>() != null) return ExtraShrineKind.Challenge;
        if (go.GetComponentInChildren<InteractableShrineMagnet>() != null) return ExtraShrineKind.Magnet;
        if (go.GetComponentInChildren<InteractableShrineCursed>() != null) return ExtraShrineKind.Cursed;
        if (go.GetComponentInChildren<InteractableShrineGreed>() != null) return ExtraShrineKind.Greed;
        if (go.GetComponentInChildren<InteractableShrineBalance>() != null) return ExtraShrineKind.Balance;
        if (go.GetComponentInChildren<InteractableShrineMoai>() != null) return ExtraShrineKind.Moai;
        if (go.GetComponentInChildren<ChargeShrine>() != null) return ExtraShrineKind.Charge;
        return null;
    }
}
