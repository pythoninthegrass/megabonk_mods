using System.Collections.Generic;

namespace MegabonkLevels;

public static class ObjectPicker
{
    // Index of the position nearest (x, z) on the ground plane within maxDistance, or -1 when none is in range.
    public static int NearestIndex(IReadOnlyList<(float X, float Z)> positions, float x, float z, float maxDistance)
    {
        var best = -1;
        var bestSquared = maxDistance * maxDistance;
        for (var i = 0; i < positions.Count; i++)
        {
            var dx = positions[i].X - x;
            var dz = positions[i].Z - z;
            var squared = dx * dx + dz * dz;
            if (squared <= bestSquared)
            {
                best = i;
                bestSquared = squared;
            }
        }

        return best;
    }
}
