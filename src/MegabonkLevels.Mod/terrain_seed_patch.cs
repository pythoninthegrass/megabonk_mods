using System;
using System.Globalization;
using HarmonyLib;
using Il2Cpp;
using Il2CppInterop.Runtime.InteropTypes;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Opt-in development measurement of the terrain seed, noise call and mesh-input grid.
public static class TerrainSeedPatch
{
    private static MelonLogger.Instance _logger;

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
        if (TerrainSeedMeasurement.IsEnabled)
        {
            _logger?.Msg("TerrainSeed: measurement enabled; a seeded harness load pins the terrain generation seed.");
        }
    }

    // Reissue with a value argument: ref-argument mutation corrupts this native interop call.
    [HarmonyPatch(typeof(MapGenerator), nameof(MapGenerator.GenerateMap), new[] { typeof(MapData), typeof(StageData), typeof(int) })]
    private static class GenerateMapSeedsTheTerrain
    {
        private static bool _pinnedCall;

        private static bool Prefix(MapData mapData, StageData stageData, int seed, MapGenerator __instance)
        {
            if (!TerrainSeedMeasurement.IsEnabled || _pinnedCall)
            {
                return true;
            }

            var pin = TerrainSeedMeasurement.TakePin();
            if (!pin.HasValue)
            {
                _logger?.Msg($"TerrainSeed: seed={seed} left to the game stage={Stage(stageData)}");
                return true;
            }

            _logger?.Msg($"TerrainSeed: pinned seed={pin.Value} (the game rolled {seed}) stage={Stage(stageData)}");
            _pinnedCall = true;
            try
            {
                __instance.GenerateMap(mapData, stageData, pin.Value);
            }
            finally
            {
                _pinnedCall = false;
            }

            return false;
        }
    }

    // Ground truth that the seed reached the noise function, which seeds System.Random per octave and reads no other
    // randomness source: the same seed and the same noise settings can only produce one grid.
    [HarmonyPatch(typeof(Noise), nameof(Noise.GenerateNoiseMap))]
    private static class NoiseUsesTheSeededGrid
    {
        private static void Prefix(
            int seed,
            float scale,
            int octaves,
            float persistance,
            float lacunarity,
            float blend,
            float blendStrength)
        {
            if (!TerrainSeedMeasurement.IsEnabled)
            {
                return;
            }

            _logger?.Msg($"TerrainSeed: noise seed={seed} scale={scale:0.####} octaves={octaves}"
                         + $" persistance={persistance:0.####} lacunarity={lacunarity:0.####}"
                         + $" blend={blend:0.####} blendStrength={blendStrength:0.####}");
        }
    }

    // Capture the actual mesh input; generator fields are only corroborating reads.
    [HarmonyPatch(typeof(Il2Cpp.MeshGenerator), nameof(Il2Cpp.MeshGenerator.GenerateTerrainMesh))]
    private static class HashesTheTerrainGrid
    {
        private static void Prefix(Il2CppObjectBase heightMap)
        {
            if (!TerrainSeedMeasurement.IsEnabled)
            {
                return;
            }

            var generator = MapGenerator.Instance ?? UnityEngine.Object.FindObjectOfType<MapGenerator>();
            _logger?.Msg($"TerrainSeed: mesh from generator={generator?.name ?? "<none>"} chunkSize={MapGenerator.mapChunkSize}");
            Hash("meshArgument", heightMap);
            Hash("heightMap", generator?.heightMap);
            Hash("staticNoiseMap", MapGenerator.staticNoiseMap);
        }
    }

    static void Hash(string label, Il2CppInterop.Runtime.InteropTypes.Il2CppObjectBase grid)
    {
        var cells = TerrainGrid.Read(grid, expectedCells: 0, out var via);
        var hash = TerrainHash.Of(cells, out var cellCount);
        var pointer = grid == null || grid.Pointer == IntPtr.Zero ? "<null>" : $"0x{grid.Pointer.ToInt64():X}";
        var summary = TerrainGridLayout.Of(cells);
        var range = summary is not { } stats
            ? string.Empty
            : $" min={stats.Min.ToString("F4", CultureInfo.InvariantCulture)}"
              + $" max={stats.Max.ToString("F4", CultureInfo.InvariantCulture)}"
              + $" mean={stats.Mean.ToString("F4", CultureInfo.InvariantCulture)}";
        _logger?.Msg($"TerrainSeed: {label} hash={(hash ?? "<none>")} cells={cellCount} read={via} ptr={pointer}{range}");
    }

    static string Stage(StageData stageData)
    {
        return stageData == null ? "<none>" : stageData.name ?? "<unnamed>";
    }
}
