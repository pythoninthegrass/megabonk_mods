namespace MegabonkLevels;

// Optional per-load replacements for a level file's map, stage, tier and seed; the file on disk is never touched.
public readonly record struct LoadOverrides(int? Map = null, int? StageIndex = null, int? Tier = null, int? Seed = null)
{
    public LevelFile Apply(LevelFile level) => level with
    {
        Map = Map is int map ? (EMap)map : level.Map,
        StageIndex = StageIndex ?? level.StageIndex,
        Tier = Tier ?? level.Tier,
        Seed = Seed ?? level.Seed,
    };
}
