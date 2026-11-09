using System.Collections.Generic;

namespace MegabonkLevels;

// Picks the rail a player moves onto when a grind runs off the end of one; the game's own catch misses a rail whose end meets another at an angle.
public static class RailHandoff
{
    // A rail's collider stops short of its spline by about 3.5% of the rail's length at each end, about 1.8 units on the long mesh rail.
    public const float SearchRadius = 3.5f;

    // How close to either end of a rail counts as landing near it, where a grind started there would stop at once.
    public const float NearEndFraction = 0.15f;

    // The game clamps a rail's progress to 0..1 and stops the grind at either end, so an interior value means the player jumped off.
    public static bool ReachedEnd(float progress) => progress >= 1f || progress <= 0f;

    // The game's direction multiplier for a rail started where the player stands: toward the far end, so a sharp turn at the joint does not start the grind running off the end it is at.
    public static float DirectionAwayFromNearestEnd(float progress) => progress >= 0.5f ? -1f : 1f;

    // The direction to start a freshly caught rail running: away from the end the player landed near, or null to leave the
    // game's own choice where the middle of the rail would carry them along anyway.
    public static float? DirectionForFreshCatch(float progress) =>
        progress <= NearEndFraction ? 1f : progress >= 1f - NearEndFraction ? -1f : (float?)null;

    // Index of the closest rail within SearchRadius that is not on cooldown, or -1.
    public static int PickNearest(IReadOnlyList<float> distances, IReadOnlyList<bool> onCooldown) =>
        PickNearest(distances, onCooldown, SearchRadius);

    // Index of the closest rail within radius that is not on cooldown, or -1.
    public static int PickNearest(IReadOnlyList<float> distances, IReadOnlyList<bool> onCooldown, float radius)
    {
        var best = -1;
        for (var i = 0; i < distances.Count; i++)
        {
            if (onCooldown[i] || distances[i] > radius)
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
