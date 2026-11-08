namespace MegabonkLevels;

// One-shot terrain-seed pin, armed only by an explicitly enabled development load.
public static class TerrainSeedMeasurement
{
    public const string EnvironmentVariable = "MEGABONK_DEV_TERRAIN_SEED";

    private static int? _pending;

    public static bool IsEnabled => EnvFlag.IsSet(EnvironmentVariable) && EnvFlag.IsSet("MEGABONK_DEV");

    public static bool IsArmed => _pending.HasValue;

    public static void Arm(int? forcedSeed, bool development, bool enabled)
    {
        _pending = development && enabled ? forcedSeed : null;
    }

    public static int? TakePin()
    {
        var pinned = _pending;
        _pending = null;
        return pinned;
    }

    public static void Reset() => _pending = null;
}
