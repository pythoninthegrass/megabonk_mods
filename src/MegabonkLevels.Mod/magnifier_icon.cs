using System;

namespace MegabonkLevels;

// Unity-free pixel mask of a magnifying glass, drawn so the palette does not depend on a font glyph.
public static class MagnifierIcon
{
    // Indexed [row, column] with row 0 at the top.
    public static bool[,] Mask(int size)
    {
        var mask = new bool[size, size];
        var centre = (int)(size * 2f / 5f);
        var outer = size * 0.33f;
        var thickness = Math.Max(1.5f, size / 10f);
        var handleStart = centre + outer * 0.7f;
        for (var row = 0; row < size; row++)
        {
            for (var column = 0; column < size; column++)
            {
                var distance = MathF.Sqrt((row - centre) * (row - centre) + (column - centre) * (column - centre));
                var onRing = distance <= outer && distance >= outer - thickness;
                var onHandle = row == column && row >= handleStart && row < size - 1;
                mask[row, column] = onRing || onHandle || IsHandleNeighbour(row, column, handleStart, size, thickness);
            }
        }

        return mask;
    }

    private static bool IsHandleNeighbour(int row, int column, float handleStart, int size, float thickness) =>
        thickness > 2f && Math.Abs(row - column) == 1 && Math.Min(row, column) >= handleStart && Math.Max(row, column) < size - 1;
}
