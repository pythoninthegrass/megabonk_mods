using HarmonyLib;
using UnityEngine;

namespace MegabonkLevels;

// Keeps the Forest grass out of cells whose ground the level repaints (desert, dungeon, hell, lava): once the grass manager
// has planted a chunk, the blades standing on a ground zone are dropped before the chunk is drawn.
public static class GrassMask
{
    private static ModLogger _logger;
    private static bool _loggedFirst;

    public static void Install(ModLogger logger) => _logger = logger;

    [HarmonyPatch(typeof(GrassChunkManager), "GenerateGrassForChunk")]
    private static class DropGrassOnRepaintedGround
    {
        private static void Postfix(GrassChunkManager __instance, Vector2Int chunkCoord)
        {
            if (!CustomLevelState.IsActive) return;
            var zones = LiveEditPatch.CurrentSettings.GroundZones;
            var size = LiveEditPatch.TileGen?.currentMapParameters?.size ?? 0;
            if (zones == null || zones.Count == 0 || size == 0) return;
            var chunks = __instance.precomputedGrassPositions;
            if (chunks == null || !chunks.TryGetValue(chunkCoord, out var blades) || blades == null) return;

            var removed = 0;
            for (var i = blades.Count - 1; i >= 0; i--)
            {
                var at = blades[i].position;
                var (cellX, cellZ) = LavaZones.CellOf(size, size, at.x, at.z);
                if (GroundZones.MaterialAt(zones, cellX, cellZ) == null) continue;
                blades.RemoveAt(i);
                removed++;
            }

            if (!_loggedFirst && removed > 0)
            {
                _loggedFirst = true;
                _logger?.Msg($"GrassMask: dropped {removed} blades on repainted ground in chunk {chunkCoord}");
            }
        }
    }
}
