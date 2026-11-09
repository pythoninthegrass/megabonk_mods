using System;
using System.Collections.Generic;
using UnityEngine;

namespace MegabonkLevels;

// Subscribes to MapGenerationController.A_GenerationComplete and logs the seed, spawned-tile counts,
// and a deterministic hash of every spawned tile/object's transform. World transforms are hashed
// (rather than a newRoot hierarchy walk) because newRoot is empty/reparented by the time this event
// fires; tiles/flatTiles/fillTiles are the lists that still hold live GameObjects at this point.
public static class GenerationPatch
{
    private const string CloneSuffix = "(Clone)";
    private const string TileObjectsParentName = "TileObjectsParent";

    public static void Install(ModLogger logger)
    {
        MapGenerationController.A_GenerationComplete += (Il2CppSystem.Action)(() => OnGenerationComplete(logger));
    }

    private static void OnGenerationComplete(ModLogger logger)
    {
        var controller = UnityEngine.Object.FindObjectOfType<MapGenerationController>();
        var tiles = controller?.proceduralTileGeneration;
        var currentMap = Assets.Scripts.Managers.MapController.currentMap;

        var seen = new HashSet<int>();
        var records = new List<SpawnRecord>();
        CollectDistinct(tiles?.tiles, seen, records);
        CollectDistinct(tiles?.flatTiles, seen, records);
        CollectDistinct(tiles?.fillTiles, seen, records);

        var objectRecords = CollectSpawnedObjects(controller);

        var snapshot = new GenerationSnapshot(
            MapGenerationController.mapSeed,
            tiles?.debugSeed ?? -1,
            currentMap?.name ?? "",
            currentMap != null ? (int)currentMap.mapType : -1,
            tiles?.tiles?.Count ?? -1,
            tiles?.flatTiles?.Count ?? -1,
            tiles?.fillTiles?.Count ?? -1,
            records.Count,
            GenerationHash.Compute(records),
            objectRecords.Count,
            GenerationHash.Compute(objectRecords));
        logger.Msg(GenerationReport.Format(snapshot));
        var support = EditorMode.CurrentMapSupport();
        if (!support.Supported)
        {
            logger.Warning($"EditorMode: unsupported map: {support.Reason}");
        }
    }

    private static List<SpawnRecord> CollectSpawnedObjects(MapGenerationController controller)
    {
        var records = new List<SpawnRecord>();
        if (controller == null)
        {
            return records;
        }

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

            records.Add(ToRecord(root.transform));
        }

        return records;
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
