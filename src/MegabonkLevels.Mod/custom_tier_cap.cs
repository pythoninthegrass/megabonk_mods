using System;

namespace MegabonkLevels;

// Custom levels are built for the game's Tier 1 (mapTierIndex 0), the only tier that never offers a portal to a stage no custom level exists for.
public static class CustomTierCap
{
    public const int MaxTier = 0;

    public static int Clamp(int tier) => Math.Min(tier, MaxTier);

    public static bool IsCapped(int tier) => tier > MaxTier;
}
