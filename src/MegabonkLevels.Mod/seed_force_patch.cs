using HarmonyLib;
using Il2Cpp;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

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

    // Object placement draws from two independent RNGs, neither tied to the tile grid's debugSeed:
    // positions via UnityEngine.Random, and per-prefab counts via RandomMapObject.GetAmount() ->
    // Utility.MyRandom.random, a static ConsistentRandom seeded once from QueryPerformanceCounter
    // (wall clock) in its static constructor. Without controlling the count RNG, counts drift every
    // run and cascade into different positions even when UnityEngine.Random is reseeded. Reseed both
    // before every spawn sub-phase (phases run across coroutine frames sharing process-wide RNG state)
    // with a phase-distinct derived seed so each phase reproduces independently of inter-phase drift.
    private static void ReseedPhase(int phase)
    {
        var baseSeed = SpawnSeed.ForcedSeed(Mode, FixedSeed, LevelSeedValue);
        if (baseSeed == null)
        {
            return;
        }

        var phaseSeed = SpawnSeed.PhaseSeed(baseSeed.Value, phase);
        Random.InitState(phaseSeed);
        Il2CppUtility.MyRandom.random = new Il2Cpp.ConsistentRandom(phaseSeed);
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

    // Each object-spawn sub-phase rolls UnityEngine.Random independently of the tile grid's debugSeed.
    // Reseeding each phase with a phase-distinct derived seed pins object placement reproducibly.
    [HarmonyPatch(typeof(GenerateTileObjects), nameof(GenerateTileObjects.Generate))]
    private static class GenerateTileObjectsPrefix
    {
        private static void Prefix() => ReseedPhase(1);
    }

    [HarmonyPatch(typeof(SpawnInteractables), nameof(SpawnInteractables.SpawnChests))]
    private static class SpawnChestsPrefix
    {
        private static void Prefix() => ReseedPhase(2);
    }

    [HarmonyPatch(typeof(SpawnInteractables), nameof(SpawnInteractables.SpawnShrines))]
    private static class SpawnShrinesPrefix
    {
        private static void Prefix() => ReseedPhase(3);
    }

    [HarmonyPatch(typeof(RandomObjectPlacer), nameof(RandomObjectPlacer.GenerateInteractables))]
    private static class GenerateInteractablesPrefix
    {
        private static void Prefix() => ReseedPhase(4);
    }
}
