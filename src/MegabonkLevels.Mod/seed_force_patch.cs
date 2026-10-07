using HarmonyLib;
using Il2Cpp;
using MelonLoader;

namespace MegabonkLevels;

public enum SeedForceMode
{
    Off,
    DebugSeed,
    MapSeedOnly,
}

// F9-cycled determinism test harness for TASK-002.02: forces generation through one candidate
// seed field at a time so which field (if either) actually drives ProceduralTileGeneration can be
// confirmed by direct testing rather than assumed from dump.cs field names.
public static class SeedForcePatch
{
    public const int FixedSeed = 20261007;

    public static SeedForceMode Mode { get; private set; } = SeedForceMode.Off;

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
            }
        }
    }
}
