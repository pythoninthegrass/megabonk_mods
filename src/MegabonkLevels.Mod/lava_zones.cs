using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// A rectangle of grid cells, ends included, that hurts a player standing on it: `Damage` hit points every `Interval` seconds.
public readonly record struct LavaZone(int MinX, int MaxX, int MinZ, int MaxZ, float Damage, float Interval);

public static class LavaZones
{
    public const float BodyCentreAboveFeet = 1.925f;
    // A player whose feet are within this far above the surface still burns; a full jump clears it.
    public const float Reach = 1.5f;
    public const float TileWidth = 40f;
    public const float MaxDamage = 1000f;
    public const float MinInterval = 0.1f;
    public const float MaxInterval = 60f;

    public static bool Contains(float minX, float maxX, float minZ, float maxZ, float surfaceY, float x, float y, float z)
    {
        var feet = y - BodyCentreAboveFeet;
        return x >= minX && x <= maxX && z >= minZ && z <= maxZ && feet >= surfaceY - 1f && feet <= surfaceY + Reach;
    }

    // The cell holding a world point when the generator centres its square grid on the origin, as a from-scratch level does.
    public static (int X, int Z) CellOf(int width, int depth, float x, float z)
    {
        var centre = (Math.Max(width, depth) - 1) / 2f;
        return ((int)MathF.Floor(x / TileWidth + centre + 0.5f), (int)MathF.Floor(z / TileWidth + centre + 0.5f));
    }

    // A message when the spawn stands on a lava zone, so a run can never begin in lava; null when it is safe.
    public static string SpawnRefusal(LevelGrid grid, IReadOnlyList<float> spawn, IReadOnlyList<LavaZone> zones)
    {
        if (zones == null || spawn is not { Count: 3 }) return null;
        var (cx, cz) = CellOf(grid.Width, grid.Depth, spawn[0], spawn[2]);
        foreach (var zone in zones)
        {
            if (cx >= zone.MinX && cx <= zone.MaxX && cz >= zone.MinZ && cz <= zone.MaxZ)
            {
                return $"The player spawn at cell ({cx}, {cz}) is inside a lava zone; move the spawn or the lava.";
            }
        }

        return null;
    }

    public static void Validate(IReadOnlyList<LavaZone> zones)
    {
        if (zones == null) return;
        foreach (var zone in zones)
        {
            if (zone.MinX < 0 || zone.MinZ < 0 || zone.MinX > zone.MaxX || zone.MinZ > zone.MaxZ
                || !float.IsFinite(zone.Damage) || zone.Damage <= 0 || zone.Damage > MaxDamage
                || !float.IsFinite(zone.Interval) || zone.Interval < MinInterval || zone.Interval > MaxInterval)
            {
                throw new ArgumentException($"Each lava zone is a cell range with 0 <= min <= max, a damage in (0, {MaxDamage}] and an interval of {MinInterval} to {MaxInterval} seconds.");
            }
        }
    }
}
