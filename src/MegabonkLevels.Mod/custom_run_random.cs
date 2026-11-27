using System;
using System.Collections.Generic;

namespace MegabonkLevels;

public sealed class CustomRunRandom
{
    private readonly HashSet<string> _usedBosses = new(StringComparer.OrdinalIgnoreCase);
    private Random _bossSelection;

    public Random ShrinePlan { get; private set; }
    public Random ShrinePlacement { get; private set; }
    public Random PowerupPlacement { get; private set; }

    public CustomRunRandom(int seed) => Reset(seed);

    public void Reset(int seed)
    {
        ResetPlacements(seed);
        _bossSelection = new Random(SpawnSeed.PhaseSeed(seed, 103));
        _usedBosses.Clear();
    }

    public void ResetPlacements(int seed)
    {
        ShrinePlan = new Random(SpawnSeed.PhaseSeed(seed, 101));
        ShrinePlacement = new Random(SpawnSeed.PhaseSeed(seed, 102));
        PowerupPlacement = new Random(SpawnSeed.PhaseSeed(seed, 104));
    }

    public string PickBoss(IReadOnlyList<string> pool) => BossPools.Pick(pool, _bossSelection, _usedBosses);
}
