using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// Best-of-set selection shared by boss copies and shrines: the candidate whose nearest already-taken spot is farthest away.
public static class Maximin
{
    // With nothing taken yet the first candidate wins.
    public static bool Pick<T>(IReadOnlyList<T> candidates, IReadOnlyList<T> taken, Func<T, T, float> distance, out T pick)
    {
        pick = default;
        var bestScore = float.MinValue;
        foreach (var candidate in candidates)
        {
            var score = float.MaxValue;
            foreach (var other in taken)
            {
                score = Math.Min(score, distance(candidate, other));
            }

            if (score > bestScore)
            {
                bestScore = score;
                pick = candidate;
            }
        }

        return candidates.Count > 0;
    }
}
