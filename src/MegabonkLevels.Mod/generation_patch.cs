using System.Collections.Generic;
using Il2Cpp;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Subscribes to MapGenerationController.A_GenerationComplete and logs the seed, spawned-tile counts,
// and a deterministic hash of every spawned tile/object's transform. World transforms are hashed
// (rather than a newRoot hierarchy walk) because newRoot is empty/reparented by the time this event
// fires; tiles/flatTiles/fillTiles are the lists that still hold live GameObjects at this point.
public static class GenerationPatch
{
    public static void Install(MelonLogger.Instance logger)
    {
        MapGenerationController.A_GenerationComplete += (Il2CppSystem.Action)(() => OnGenerationComplete(logger));
    }

    private static void OnGenerationComplete(MelonLogger.Instance logger)
    {
        var controller = UnityEngine.Object.FindObjectOfType<MapGenerationController>();
        var tiles = controller?.proceduralTileGeneration;
        var currentMap = Il2CppAssets.Scripts.Managers.MapController.currentMap;

        var seen = new HashSet<int>();
        var records = new List<SpawnRecord>();
        CollectDistinct(tiles?.tiles, seen, records);
        CollectDistinct(tiles?.flatTiles, seen, records);
        CollectDistinct(tiles?.fillTiles, seen, records);

        var snapshot = new GenerationSnapshot(
            MapGenerationController.mapSeed,
            tiles?.debugSeed ?? -1,
            currentMap?.name ?? "",
            currentMap != null ? (int)currentMap.mapType : -1,
            tiles?.tiles?.Count ?? -1,
            tiles?.flatTiles?.Count ?? -1,
            tiles?.fillTiles?.Count ?? -1,
            records.Count,
            GenerationHash.Compute(records));
        logger.Msg(GenerationReport.Format(snapshot));
    }

    private static void CollectDistinct(Il2CppSystem.Collections.Generic.List<GameObject> source, HashSet<int> seen, List<SpawnRecord> records)
    {
        if (source == null)
        {
            return;
        }

        for (var i = 0; i < source.Count; i++)
        {
            var go = source[i];
            if (go == null || !seen.Add(go.GetInstanceID()))
            {
                continue;
            }

            records.Add(ToRecord(go.transform));
        }
    }

    private static SpawnRecord ToRecord(Transform t)
    {
        var p = t.position;
        var r = t.rotation;
        var s = t.lossyScale;
        return new SpawnRecord(t.name, p.x, p.y, p.z, r.x, r.y, r.z, r.w, s.x, s.y, s.z);
    }
}
