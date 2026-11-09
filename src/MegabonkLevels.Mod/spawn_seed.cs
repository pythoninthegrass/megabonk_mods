namespace MegabonkLevels;

public enum SeedForceMode
{
    Off,
    DebugSeed,
    MapSeedOnly,
    LevelSeed,
}

// Decides the UnityEngine.Random seed to force before the random-object/chest/shrine spawners, which
// roll independently of ProceduralTileGeneration.debugSeed. Only the modes that force debugSeed (the
// generation seed) reseed the spawners too, so object placement reproduces alongside the tile grid.
public static class SpawnSeed
{
    public static int? ForcedSeed(SeedForceMode mode, int fixedSeed, int levelSeedValue) => mode switch
    {
        SeedForceMode.DebugSeed => fixedSeed,
        SeedForceMode.LevelSeed => levelSeedValue,
        _ => null,
    };

    // Derives a stable, phase-distinct seed so each object-spawn sub-phase reproduces independently of
    // UnityEngine.Random drift caused by unrelated callers between phases. Pure, deterministic mix.
    public static int PhaseSeed(int baseSeed, int phase)
    {
        unchecked
        {
            var h = (uint)baseSeed * 2654435761u;
            h ^= (uint)phase * 2246822519u;
            h ^= h >> 15;
            h *= 2654435761u;
            h ^= h >> 13;
            return (int)h;
        }
    }
}
