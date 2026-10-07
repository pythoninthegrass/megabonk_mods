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

// BFS reachability over LevelState's tile grid using the "chain/slope rule" from the AlexK maze-chain
// reference (see TASK-003's description): two adjacent tiles at equal height are always connected; a
// 1-unit height difference is only connected where a slope bridges it.
//
// TODO(TASK-003.04): slope ownership/direction is an assumption, not yet confirmed against real game
// data. TASK-002.03 confirmed the tile grid's shape and spacing but not which tile "owns" a slope at a
// given height step or which way SlopeDirection points relative to travel direction. This implementation
// assumes a slope's SlopeDirection is set on the HIGHER of the two tiles and points downhill, toward the
// lower neighbor (i.e. it names the direction you'd walk off the ramp, not the direction you climbed to
// reach it). Revisit this once real runtime slope data is available.
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

    // directionFromTo is the direction of travel from `from` to `to`. Legal when heights match, or when
    // the two differ by exactly one and the higher tile's slope points downhill toward the lower one —
    // see the ownership/direction TODO on this class.
    private static bool CanTraverse(TileState from, TileState to, SlopeDirection directionFromTo)
    {
        if (from.Height == to.Height)
        {
            return true;
        }

        if (to.Height == from.Height + 1)
        {
            return to.Slope == Opposite(directionFromTo);
        }

        if (from.Height == to.Height + 1)
        {
            return from.Slope == directionFromTo;
        }

        return false;
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
