namespace MegabonkLevels;

public readonly record struct FromScratchTile(int X, int Z, int Height, bool IsSlope, int DirectionX, int DirectionZ);

// Unity-free layout rules for building a from-scratch level's grid on the game's tile generator.
public static class FromScratchLayout
{
    public static string SizeRefusal(LevelGrid grid, int stockSize) =>
        grid.Width > stockSize || grid.Depth > stockSize
            ? $"grid {grid.Width}x{grid.Depth} is larger than the kit's stock size {stockSize}x{stockSize}"
            : null;

    // The game's tile array is square, so a rectangular grid is built inside the longer side.
    public static int GeneratorSize(LevelGrid grid) => System.Math.Max(grid.Width, grid.Depth);

    // A flat tile faces +Z like a freshly instantiated one; a slope faces its uphill side.
    public static FromScratchTile TileArguments(AuthoredCell cell)
    {
        var isSlope = cell.Slope != SlopeDirection.None;
        var (dx, dz) = isSlope ? TilePlacement.UphillVector(cell.Slope) : (0, 1);
        return new FromScratchTile(cell.X, cell.Z, cell.Height, isSlope, dx, dz);
    }

    public static bool IsInPlace(System.Collections.Generic.IReadOnlyList<float> current, System.Collections.Generic.IReadOnlyList<float> target, float tolerance)
    {
        if (current is not { Count: 3 } || target is not { Count: 3 })
        {
            return false;
        }

        for (var axis = 0; axis < 3; axis++)
        {
            if (System.Math.Abs(current[axis] - target[axis]) > tolerance)
            {
                return false;
            }
        }

        return true;
    }
}
