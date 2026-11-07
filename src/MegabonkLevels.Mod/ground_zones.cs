using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// A rectangle of grid cells, ends included, whose ground tiles are drawn with the named game material.
public readonly record struct GroundZone(string Material, int MinX, int MaxX, int MinZ, int MaxZ);

public static class GroundZones
{
    // The material of the last zone holding the cell, so a later zone paints over an earlier one; null when no zone holds it.
    public static string MaterialAt(IReadOnlyList<GroundZone> zones, int x, int z)
    {
        if (zones == null) return null;
        for (var i = zones.Count - 1; i >= 0; i--)
        {
            var zone = zones[i];
            if (x >= zone.MinX && x <= zone.MaxX && z >= zone.MinZ && z <= zone.MaxZ) return zone.Material;
        }

        return null;
    }

    public static void Validate(IReadOnlyList<GroundZone> zones)
    {
        if (zones == null) return;
        foreach (var zone in zones)
        {
            if (string.IsNullOrWhiteSpace(zone.Material) || zone.MinX < 0 || zone.MinZ < 0 || zone.MinX > zone.MaxX || zone.MinZ > zone.MaxZ)
            {
                throw new ArgumentException("Each ground zone names a material and a cell range with 0 <= min <= max on both axes.");
            }
        }
    }
}
