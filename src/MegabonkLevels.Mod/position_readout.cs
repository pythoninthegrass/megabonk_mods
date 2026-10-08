using System;
using System.Globalization;

namespace MegabonkLevels;

// A tile grid cell; InGrid is false when the position lies outside the grid, and X and Z are then the unclamped
// cell indices the position would have.
public readonly record struct GridCell(int X, int Z, bool InGrid);

// Unity-free rules for the dev readout of where the player is. The grid is centred on the world origin, so cell
// (x, z) of a width x depth grid sits at ((x - (width - 1) / 2) * spacing, (z - (depth - 1) / 2) * spacing).
public static class PositionReadout
{
    // A cell owns the half-open span of half a spacing either side of its centre, lower edge included.
    public static GridCell CellOf(float x, float z, int width, int depth, float spacing)
    {
        var cellX = (int)MathF.Floor(x / spacing + (width - 1) / 2f + 0.5f);
        var cellZ = (int)MathF.Floor(z / spacing + (depth - 1) / 2f + 0.5f);
        return new GridCell(cellX, cellZ, cellX >= 0 && cellX < width && cellZ >= 0 && cellZ < depth);
    }

    public static int LevelOf(float y, float tileHeight) => (int)MathF.Round(y / tileHeight, MidpointRounding.AwayFromZero);

    public static string Format(float x, float y, float z, GridCell cell, int level, float floorY)
    {
        var text = Describe(x, y, z, cell, level);
        if (float.IsNegativeInfinity(floorY))
        {
            return text;
        }

        text += $"  floor {Whole(floorY)}";
        return KillFloor.ShouldKill(y, floorY) ? text + BelowFloorFlag : text;
    }

    // One line for a boss or enemy: the floor height is already on the player's line, so only the flag is added.
    public static string FormatActor(string label, float x, float y, float z, GridCell cell, int level, float floorY)
    {
        var text = $"{label} {Describe(x, y, z, cell, level)}";
        return KillFloor.ShouldKill(y, floorY) ? text + BelowFloorFlag : text;
    }

    private const string BelowFloorFlag = "  BELOW FLOOR";

    private static string Describe(float x, float y, float z, GridCell cell, int level)
    {
        var cellText = $"cell ({cell.X},{cell.Z}){(cell.InGrid ? string.Empty : " outside")}";
        return $"{cellText} h{level}  pos ({Whole(x)}, {Whole(y)}, {Whole(z)})";
    }

    // Casting to int drops the sign of a negative zero, which would otherwise print as "-0".
    private static string Whole(float value) => ((int)MathF.Round(value, MidpointRounding.AwayFromZero)).ToString(CultureInfo.InvariantCulture);
}
