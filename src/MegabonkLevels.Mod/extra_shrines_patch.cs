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
        var onMesh = settings.ShrineSpots != null;
        if (!onMesh && (tiles == null || ground == null || state.Tiles.Count == 0))
        {
            logger.Warning("ExtraShrines: no tile ground available; no extra shrines spawned");
            return;
        }

        var allowed = AllowedKindsFromSettings(settings, logger);
        var guaranteed = ExtraShrines.ParseKinds(settings.GuaranteedShrineKinds);
        if (ReferenceEquals(allowed, s_skipPass))
        {
            if (guaranteed.Count == 0 && settings.ShrineKindRanges is not { Count: > 0 }) return;
            allowed = new HashSet<ExtraShrineKind>();
        }

        var ranged = ExtraShrines.RangedKinds(settings.ShrineKindRanges, new System.Random(System.Guid.NewGuid().GetHashCode()));
        var poolKinds = allowed == null ? null : allowed.Concat(guaranteed).Concat(ranged).ToHashSet();
        var pool = BuildPool(settings, controller, poolKinds, logger);
        if (pool.Count == 0) return;

        Physics.SyncTransforms();
        var start = settings.PlayerStart is { Count: 3 }
            ? new Vector3(settings.PlayerStart[0], settings.PlayerStart[1], settings.PlayerStart[2])
            : MapGenerationController.tileSpawnPosition;
        var (anchors, routes) = HotPathGeometry(controller, start);
        var existing = ExistingShrinePositions(index);
        var random = new System.Random(System.Guid.NewGuid().GetHashCode());
        var requested = ExtraShrines.ShrineCount(settings.ExtraShrines, settings.ExtraShrinesMax, random);
        if (onMesh)
        {
            var randomPool = pool.Where(entry => allowed == null || allowed.Contains(entry.Kind)).ToList();
            var plan = ExtraShrines.Shuffled(guaranteed.Concat(ranged).Concat(Enumerable.Range(0, randomPool.Count == 0 ? 0 : requested).Select(_ => randomPool[random.Next(randomPool.Count)].Kind)).ToList(), random);
            var meshSpawned = SpawnAtAuthoredSpots(settings, index, pool, plan, random, logger);
            logger.Msg($"ExtraShrines: spawned={meshSpawned} planned={plan.Count} guaranteed={guaranteed.Count} ranged={ranged.Count} spots={settings.ShrineSpots.Count} pool={pool.Count} path=spots");
            return;
        }

        if (ranged.Count > 0) logger.Warning("ExtraShrines: shrineKindRanges need shrineSpots and are ignored on the tile probe path");
        var points = PlacementProbe.ReachablePoints(state, tiles, ground, start, logger, "ExtraShrines").Values.ToList();
        var spacing = tiles.currentMapParameters.scaledTileWidth / PlacementProbe.SamplesPerTile;
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

                    if (!TryPlace(entry, floor, ground, index, out position, out _, out _)) return false;
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

        logger.Msg($"ExtraShrines: spawned={spawned} requested={requested} pool={pool.Count} reachableFlatSamples={points.Count} path=tiles");
    }

    // The level authors where its shrines may stand, so no probing is needed: each spot is drawn with a preference for ones far
    // from the shrines already placed, and kept where a shrine fits, looking outward from it in rings until one does.
    private static int SpawnAtAuthoredSpots(LevelFile settings, IReadOnlyDictionary<string, GameObject> index, List<PoolEntry> pool,
        IReadOnlyList<ExtraShrineKind> plan, System.Random random, MelonLogger.Instance logger)
    {
        var offsets = ExtraShrines.NudgeOffsets(ExtraShrines.NudgeStep, ExtraShrines.NudgeRings, ExtraShrines.NudgeDirections);
        var remaining = settings.ShrineSpots.Select(spot => new Vector3Data(spot[0], spot[1], spot[2])).ToList();
        var taken = new List<Vector3Data>();
        var spawned = 0;
        foreach (var kind in plan)
        {
            var ofKind = pool.Where(candidate => candidate.Kind == kind).ToList();
            if (ofKind.Count == 0)
            {
                logger.Warning($"ExtraShrines: no {kind} shrine prefab is available");
                continue;
            }

            while (true)
            {
                var pick = ExtraShrines.PickSpread(remaining, taken, random);
                if (pick < 0)
                {
                    logger.Warning($"ExtraShrines: no authored spot is left for a {kind} shrine");
                    break;
                }

                var spot = remaining[pick];
                remaining.RemoveAt(pick);
                if (TryPlaceAtSpot(ofKind[random.Next(ofKind.Count)], spot, offsets, index, random, logger))
                {
                    taken.Add(spot);
                    spawned++;
                    break;
                }
            }
        }

        return spawned;
    }

    // Looks for a place for the shrine at an authored spot: the spot itself and then rings around it, each needing clear space, and failing that the nearest floor regardless.
    private static bool TryPlaceAtSpot(PoolEntry entry, Vector3Data spot, IReadOnlyList<(float X, float Z)> offsets,
        IReadOnlyDictionary<string, GameObject> index, System.Random random, MelonLogger.Instance logger)
    {
        var (top, bottom) = ExtraShrines.SpotFloorWindow(spot.Y);
        var placed = false;
        var position = default(Vector3);
        var rejection = "no floor";
        GameObject shrine = null;
        int withFloor = 0;
        Vector3? nearestFloor = null;
        foreach (var (dx, dz) in offsets)
        {
            if (!PlacementProbe.HighestFloor(spot.X + dx, spot.Z + dz, top, bottom, null, out var floor)) continue;
            withFloor++;
            nearestFloor ??= floor;
            if (TryPlace(entry, floor, null, index, out position, out rejection, out shrine))
            {
                placed = true;
                break;
            }
        }

        // The spot is authored, so when nothing fits cleanly (a corner at the top of a quarter pipe leaves a strip narrower than the shrine) it goes on the nearest floor regardless.
        if (!placed && nearestFloor is { } tight && TryPlace(entry, tight, null, index, out position, out rejection, out shrine, requireClear: false))
        {
            placed = true;
            logger.Msg($"ExtraShrines: authored spot ({spot.X:F1}, {spot.Y:F1}, {spot.Z:F1}) is tight; placed without clearance at {position.ToString("F3")}");
        }

        if (!placed)
        {
            logger.Warning($"ExtraShrines: no {entry.Kind} shrine fits near authored spot ({spot.X:F1}, {spot.Y:F1}, {spot.Z:F1}): {rejection}; floor under {withFloor} of {offsets.Count} offsets");
            return false;
        }

        var golden = entry.Kind == ExtraShrineKind.Charge && ExtraShrines.RollGolden(random, ExtraShrines.GoldenChance);
        if (entry.Kind == ExtraShrineKind.Charge) SetRarity(shrine, golden);
        logger.Msg($"ExtraShrines: spawned {(golden ? "golden " : "")}{entry.Kind} at {position.ToString("F3")} for authored spot ({spot.X:F1}, {spot.Y:F1}, {spot.Z:F1})");
        return true;
    }

    // The game rolls golden once per shrine in Awake with a chance of under 1%, so the level's shrines get their own roll applied afterwards.
    private static void SetRarity(GameObject shrine, bool golden)
    {
        var charge = shrine.GetComponentInChildren<ChargeShrine>();
        if (charge == null) return;
        charge.isGolden = golden;
        if (golden && charge.goldMaterial != null && charge.meshRenderer != null) charge.meshRenderer.material = charge.goldMaterial;
    }

    // Instantiates a trial shrine on the floor point and keeps it only when nothing overlaps it; a tile ground also has to support its footprint. A rejection names the check that failed.
    private static bool TryPlace(PoolEntry entry, Vector3 floor, MeshCollider ground, IReadOnlyDictionary<string, GameObject> index, out Vector3 position, out string rejection, out GameObject placed, bool requireClear = true)
    {
        position = default;
        rejection = null;
        placed = null;
        var trial = CreateTrial(entry, floor);
        if (trial == null)
        {
            rejection = "noTrial";
            return false;
        }

        Physics.SyncTransforms();
        if (!PlacementProbe.TryBounds(trial, out var bounds)) rejection = "noBounds";
        else if (ground != null && !PlacementProbe.Supported(ground, ShiftedDown(bounds, floor.y), floor.y)) rejection = "unsupported";
        else if (requireClear && PlacementProbe.FirstOccupant(ShiftedDown(bounds, floor.y), floor.y, trial.transform) is { } occupant)
            rejection = $"occupied by {occupant.name} at {occupant.bounds.center.ToString("F1")}";
        else if (requireClear && PlacementProbe.OverlapsObjects(ShiftedDown(bounds, floor.y), trial, index, _spawned, levelObjects: ground != null)) rejection = "overlapsObject";
        if (rejection != null)
        {
            // Destroy only takes effect at the end of the frame, so the trial is switched off first or the next trial in the same frame would collide with it.
            trial.SetActive(false);
            UnityEngine.Object.Destroy(trial);
            return false;
        }

        trial.transform.position += Vector3.up * (floor.y - bounds.min.y);
        Physics.SyncTransforms();
        _spawned.Add(trial);
        position = trial.transform.position;
        placed = trial;
        return true;
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
    // native-up correction for their model's authored up axis.
    private static GameObject CreateTrial(PoolEntry entry, Vector3 floor)
    {
        if (entry.LiveClone != null) return UnityEngine.Object.Instantiate(entry.LiveClone, floor, entry.LiveClone.transform.rotation);
        var up = ExtraShrines.LocalUp(entry.Kind);
        var axis = new Vector3(up.X, up.Y, up.Z);
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
        if (go.GetComponentInChildren<InteractableShadyGuy>() != null) return ExtraShrineKind.ShadyGuy;
        return null;
    }
}
