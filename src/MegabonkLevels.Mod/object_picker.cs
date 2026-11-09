using System.Collections.Generic;

namespace MegabonkLevels;

// One collider along the pick ray; HitsModelBounds is whether the ray also crosses the owning object's visible model.
public readonly record struct RayHit(float Distance, bool IsTrigger, bool ResolvesToObject, bool HitsModelBounds);

public static class ObjectPicker
{
    // Index of the nearest hit that selects an object, or -1. Trigger volumes (charge radii, fade volumes) only count when the
    // ray crosses the visible model; a solid collider that is not an object, such as terrain, hides everything behind it.
    public static int NearestHit(IReadOnlyList<RayHit> hits)
    {
        var order = new List<int>(hits.Count);
        for (var i = 0; i < hits.Count; i++)
        {
            order.Add(i);
        }

        order.Sort((a, b) => hits[a].Distance.CompareTo(hits[b].Distance));
        foreach (var i in order)
        {
            var hit = hits[i];
            if (hit.ResolvesToObject && (!hit.IsTrigger || hit.HitsModelBounds))
            {
                return i;
            }

            if (!hit.IsTrigger && !hit.ResolvesToObject)
            {
                return -1;
            }
        }

        return -1;
    }

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
