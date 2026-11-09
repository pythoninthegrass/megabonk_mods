namespace MegabonkLevels;

// Optional per-load replacements for a level file's map, stage, tier and seed, plus the dev-flag character name; the file on disk is never touched.
// Unseeded leaves the seed alone and stops the mod forcing one at all, so the game rolls its own.
public readonly record struct LoadOverrides(int? Map = null, int? StageIndex = null, int? Tier = null, int? Seed = null, string Character = null, bool Unseeded = false)
{
    public LevelFile Apply(LevelFile level) => level with
    {
        Map = Map is int map ? (EMap)map : level.Map,
        StageIndex = StageIndex ?? level.StageIndex,
        Tier = Tier ?? level.Tier,
        Seed = Seed ?? level.Seed,
    };
}
