using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace MegabonkLevels;

public enum SeedForceMode
{
    Off,
    DebugSeed,
    MapSeedOnly,
    LevelSeed,
}

// F9-cycled determinism test harness for TASK-002.02 (DebugSeed/MapSeedOnly, confirmed debugSeed is
// the field that actually controls Tiles-map generation — see docs/map-generation-determinism.md),
// extended for TASK-004.01 with LevelSeed: forces a specific level file's recorded seed for exactly
// the generation(s) that follow LevelLoader starting a run, via the same debugSeed/useDebugSeed hook.
public static class SeedForcePatch
{
    public const int FixedSeed = 20261007;

    public static SeedForceMode Mode { get; private set; } = SeedForceMode.Off;

    public static int LevelSeedValue { get; private set; }

    private static MelonLogger.Instance _logger;

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    public static void CycleMode()
    {
        Mode = Mode switch
        {
            SeedForceMode.Off => SeedForceMode.DebugSeed,
            SeedForceMode.DebugSeed => SeedForceMode.MapSeedOnly,
            _ => SeedForceMode.Off,
        };
        _logger?.Msg($"SeedForcePatch mode -> {Mode} (fixedSeed={FixedSeed})");
    }

    public static void ForceLevelSeed(int seed)
    {
        LevelSeedValue = seed;
        Mode = SeedForceMode.LevelSeed;
        _logger?.Msg($"SeedForcePatch mode -> {Mode} (levelSeed={seed})");
    }

    [HarmonyPatch(typeof(ProceduralTileGeneration), nameof(ProceduralTileGeneration.Generate))]
    private static class GeneratePrefix
    {
        private static void Prefix(ProceduralTileGeneration __instance, ref bool useDebugSeed)
        {
            switch (Mode)
            {
                case SeedForceMode.DebugSeed:
                    __instance.debugSeed = FixedSeed;
                    useDebugSeed = true;
                    break;
                case SeedForceMode.MapSeedOnly:
                    MapGenerationController.mapSeed = FixedSeed;
                    break;
                case SeedForceMode.LevelSeed:
                    __instance.debugSeed = LevelSeedValue;
                    useDebugSeed = true;
                    break;
            }
        }
    }
}
