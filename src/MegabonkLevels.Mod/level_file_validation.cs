using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// Rejects level files whose baseline, grid, spawn and edits contradict each other; throws ArgumentException naming the problem.
public static class LevelFileValidator
{
    private static readonly string[] TileOpTypes =
        { SetTileHeight.OpType, SetTileSlope.OpType, AddTile.OpType, RemoveTile.OpType };

    public static void Validate(LevelFile level)
    {
        if (level.Baseline is not (null or LevelFile.GeneratedBaseline or LevelFile.NoBaseline))
        {
            throw new ArgumentException($"Unknown baseline '{level.Baseline}': expected 'generated' or 'none'.");
        }

        if (level.IsFromScratch)
        {
            ValidateFromScratch(level);
        }
        else if (level.Grid is not null)
        {
            throw new ArgumentException("A level with a generated baseline cannot have a grid; set baseline to 'none'.");
        }
    }

    private static void ValidateFromScratch(LevelFile level)
    {
        if (level.Grid is null)
        {
            throw new ArgumentException("A from-scratch level requires grid.");
        }

        if (level.Spawn is null)
        {
            throw new ArgumentException("A from-scratch level requires spawn.");
        }

        if (level.BossSpawner is null)
        {
            throw new ArgumentException("A from-scratch level requires bossSpawner.");
        }

        ValidateGrid(level.Grid.Value);

        foreach (var op in level.Edits)
        {
            if (TileOpTypes.Contains(op.OpType))
            {
                throw new ArgumentException($"A from-scratch level cannot have the tile edit '{op.OpType}': the grid is the single source of truth.");
            }

            if (op.Target is not null && op.Target.StartsWith("gen:", StringComparison.Ordinal))
            {
                throw new ArgumentException($"A from-scratch level cannot target the generated object '{op.Target}': nothing is generated.");
            }
        }
    }

    private static void ValidateGrid(LevelGrid grid)
    {
        if (grid.Width < 1 || grid.Depth < 1)
        {
            throw new ArgumentException($"grid width and depth must be positive, got {grid.Width} by {grid.Depth}.");
        }

        var seen = new HashSet<(int X, int Z)>();
        foreach (var cell in grid.Cells ?? Array.Empty<AuthoredCell>())
        {
            if (cell.X < 0 || cell.X >= grid.Width || cell.Z < 0 || cell.Z >= grid.Depth)
            {
                throw new ArgumentException($"grid cell ({cell.X}, {cell.Z}) lies outside the {grid.Width} by {grid.Depth} grid.");
            }

            if (!seen.Add((cell.X, cell.Z)))
            {
                throw new ArgumentException($"grid cell ({cell.X}, {cell.Z}) appears more than once.");
            }
        }
    }
}
