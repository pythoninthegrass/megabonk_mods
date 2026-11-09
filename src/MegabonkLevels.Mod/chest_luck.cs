using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// A level can skew every chest's loot rarity for a run: one shift is drawn per run and added to the luck the game rolls chest items with.
public static class ChestLuck
{
    // A uniform shift inside the range, or none without one.
    public static float Roll(IReadOnlyList<float> range, Random random) =>
        range == null ? 0f : range[0] + (float)random.NextDouble() * (range[1] - range[0]);

    public static float Apply(float luck, float shift) => luck + shift;
}
