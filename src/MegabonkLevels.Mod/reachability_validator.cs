using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// The full reachable/unreachable split and target-reachability answer for one BFS run from a start
// tile, per TASK-003.04. Recomputed fresh by ReachabilityValidator.Validate — not incrementally updated
// as LevelState changes, since edits are infrequent relative to how often a validation might be read.
public sealed class ReachabilityResult
{
    public IReadOnlySet<(int X, int Z)> Reachable { get; }
    public IReadOnlyList<(int X, int Z)> Unreachable { get; }

    internal ReachabilityResult(HashSet<(int X, int Z)> reachable, IReadOnlyList<(int X, int Z)> unreachable)
    {
        Reachable = reachable;
        Unreachable = unreachable;
    }

    public bool IsReachable((int X, int Z) tile) => Reachable.Contains(tile);
}

// BFS reachability over LevelState's tile grid. A flat tile has one height on all four edges. A slope tile
// at height h spans h at its downhill edge to h + 1 at its uphill edge (SlopeDirection names the uphill side,
// matching the game's ProceduralTile.dir) and has no connection through its two side edges. Two adjacent
// tiles are connected when the heights of the edges that face each other are equal.
public static class ReachabilityValidator
{
    private static readonly (int Dx, int Dz, SlopeDirection Dir)[] Neighbors =
    {
        (0, 1, SlopeDirection.North),
        (0, -1, SlopeDirection.South),
        (1, 0, SlopeDirection.East),
        (-1, 0, SlopeDirection.West),
    };

    public static ReachabilityResult Validate(LevelState state, (int X, int Z) start)
    {
        if (state.GetTile(start.X, start.Z) is null)
        {
            throw new ArgumentException($"Start tile ({start.X}, {start.Z}) does not exist in this LevelState.", nameof(start));
        }

        var reachable = new HashSet<(int X, int Z)> { start };
        var queue = new Queue<(int X, int Z)>();
        queue.Enqueue(start);

        while (queue.Count > 0)
        {
            var current = queue.Dequeue();
            var currentTile = state.GetTile(current.X, current.Z)!.Value;

            foreach (var (dx, dz, dir) in Neighbors)
            {
                var neighbor = (X: current.X + dx, Z: current.Z + dz);
                if (reachable.Contains(neighbor))
                {
                    continue;
                }

                var neighborTile = state.GetTile(neighbor.X, neighbor.Z);
                if (neighborTile is null || !CanTraverse(currentTile, neighborTile.Value, dir))
                {
                    continue;
                }

                reachable.Add(neighbor);
                queue.Enqueue(neighbor);
            }
        }

        var unreachable = state.Tiles.Keys.Where(tile => !reachable.Contains(tile)).ToList();
        return new ReachabilityResult(reachable, unreachable);
    }

    // directionFromTo is the direction of travel from `from` to `to`.
    private static bool CanTraverse(TileState from, TileState to, SlopeDirection directionFromTo)
    {
        var leaving = EdgeHeight(from, directionFromTo);
        var entering = EdgeHeight(to, Opposite(directionFromTo));
        return leaving is not null && leaving == entering;
    }

    // Height of the tile's edge on the given side, or null where a slope's side edge connects to nothing.
    private static int? EdgeHeight(TileState tile, SlopeDirection side)
    {
        if (tile.Slope == SlopeDirection.None)
        {
            return tile.Height;
        }

        if (side == tile.Slope)
        {
            return tile.Height + 1;
        }

        return side == Opposite(tile.Slope) ? tile.Height : null;
    }

    private static SlopeDirection Opposite(SlopeDirection direction) => direction switch
    {
        SlopeDirection.North => SlopeDirection.South,
        SlopeDirection.South => SlopeDirection.North,
        SlopeDirection.East => SlopeDirection.West,
        SlopeDirection.West => SlopeDirection.East,
        _ => throw new ArgumentException($"{nameof(direction)} must be a cardinal direction, got {direction}.", nameof(direction)),
    };
}
