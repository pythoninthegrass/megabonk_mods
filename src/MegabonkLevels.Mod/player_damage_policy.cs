using System;

namespace MegabonkLevels;

public static class PlayerDamagePolicy
{
    public static float Clamp(float damage, int hp, float shield, float overheal, bool nonlethal)
    {
        if (!nonlethal || shield > 0f)
        {
            return damage;
        }

        // Native HP subtraction truncates, so reserve the fractional overheal as well as 1 HP.
        return Math.Min(damage, Math.Max(0, hp - 1) + MathF.Floor(Math.Max(0f, overheal)));
    }
}
