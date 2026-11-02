using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

public enum RandomizedInteractableKind { ShadyGuy, Chest, Moai }

public static class InteractableRandomization
{
    public static bool Enabled(LevelFile level) => level.RandomizeShadyGuy || level.RandomizeChests || level.RandomizeMoai;

    public static Vector3Data LocalUp(RandomizedInteractableKind kind) => kind switch
    {
        RandomizedInteractableKind.ShadyGuy => new Vector3Data(0, 1, 0),
        RandomizedInteractableKind.Chest or RandomizedInteractableKind.Moai => new Vector3Data(0, 0, 1),
        _ => throw new ArgumentOutOfRangeException(nameof(kind)),
    };

    public static bool ShouldMove(LevelFile level, RandomizedInteractableKind kind, string genId, IReadOnlyList<EditOp> edits)
    {
        var enabled = kind switch
        {
            RandomizedInteractableKind.ShadyGuy => level.RandomizeShadyGuy,
            RandomizedInteractableKind.Chest => level.RandomizeChests,
            RandomizedInteractableKind.Moai => level.RandomizeMoai,
            _ => false,
        };
        return enabled && !edits.Any(op => op.Target == "gen:" + genId && op.OpType is MoveObject.OpType or RemoveObject.OpType);
    }

    public static bool TryChoose<T>(IReadOnlyList<T> candidates, Func<int, int> next, Func<T, bool> valid, int budget, out T chosen)
    {
        var remaining = candidates.ToList();
        for (var i = 0; i < budget && remaining.Count > 0; i++)
        {
            var index = next(remaining.Count);
            var candidate = remaining[index];
            remaining.RemoveAt(index);
            if (valid(candidate))
            {
                chosen = candidate;
                return true;
            }
        }
        chosen = default;
        return false;
    }

    public static IReadOnlySet<(int X, int Z)> ReachableSamples<T>(IReadOnlyDictionary<(int X, int Z), T> samples,
        (int X, int Z) start, Func<T, T, bool> clear)
    {
        var visited = new HashSet<(int X, int Z)>();
        if (!samples.ContainsKey(start)) return visited;
        visited.Add(start);
        var queue = new Queue<(int X, int Z)>();
        queue.Enqueue(start);
        while (queue.Count > 0)
        {
            var cell = queue.Dequeue();
            foreach (var next in new[] { (cell.X + 1, cell.Z), (cell.X - 1, cell.Z), (cell.X, cell.Z + 1), (cell.X, cell.Z - 1) })
            {
                if (visited.Contains(next) || !samples.ContainsKey(next) || !clear(samples[cell], samples[next])) continue;
                visited.Add(next);
                queue.Enqueue(next);
            }
        }
        return visited;
    }
}
