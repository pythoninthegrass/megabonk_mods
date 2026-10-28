using System.Collections.Generic;

namespace MegabonkLevels;

// Picks the rail a player moves onto when a grind runs off the end of one; the game's own catch misses a rail whose end meets another at an angle.
public static class RailHandoff
{
    // A rail's collider stops short of its spline by about 3.5% of the rail's length at each end, about 1.8 units on the long mesh rail.
    public const float SearchRadius = 3.5f;

    // The game clamps a rail's progress to 0..1 and stops the grind at either end, so an interior value means the player jumped off.
    public static bool ReachedEnd(float progress) => progress >= 1f || progress <= 0f;

    // Index of the closest rail within SearchRadius that is not on cooldown, or -1.
    public static int PickNearest(IReadOnlyList<float> distances, IReadOnlyList<bool> onCooldown)
    {
        var best = -1;
        for (var i = 0; i < distances.Count; i++)
        {
            if (onCooldown[i] || distances[i] > SearchRadius)
            {
                continue;
            }

            if (best < 0 || distances[i] < distances[best])
            {
                best = i;
            }
        }

        return best;
    }
}
