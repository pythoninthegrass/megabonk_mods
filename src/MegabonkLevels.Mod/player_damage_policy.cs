using System;

namespace MegabonkLevels;

public static class PlayerDamagePolicy
{
    public const bool IgnoreShield = true;

    public static float Clamp(float damage, int hp, float overheal, bool nonlethal)
    {
        if (!nonlethal)
        {
            return damage;
        }

        // Native HP subtraction truncates, so reserve the fractional overheal as well as 1 HP.
        return Math.Min(damage, Math.Max(0, hp - 1) + MathF.Floor(Math.Max(0f, overheal)));
    }
}
