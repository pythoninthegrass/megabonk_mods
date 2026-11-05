using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// Folds a from-scratch editing session into the level file it saves: the grid is the final tile state and the edit log
// collapses to one placement per surviving object at its final transform.
public static class FromScratchSnapshot
{
    public static LevelFile Build(LevelFile template, LevelState state, IReadOnlyList<EditOp> edits, IReadOnlyList<float> playerStart, IReadOnlyList<float> bossPosition)
    {
        var grid = template.Grid ?? throw new ArgumentException("A from-scratch template requires a grid.", nameof(template));
        var cells = state.Tiles
            .OrderBy(pair => pair.Key.X).ThenBy(pair => pair.Key.Z)
            .Select(pair => new AuthoredCell(pair.Key.X, pair.Key.Z, pair.Value.Height, pair.Value.Slope))
            .ToList();

        return template with
        {
            Grid = new LevelGrid(grid.Width, grid.Depth, cells),
            Edits = FoldObjectEdits(edits),
            Spawn = Relocated(template.Spawn, playerStart),
            BossSpawner = Relocated(template.BossSpawner, bossPosition),
            PlayerStart = null,
            BossSpawnPosition = null,
        };
    }

    private static SpawnPoint? Relocated(SpawnPoint? point, IReadOnlyList<float> position) =>
        point is { } existing && position is { Count: 3 } ? existing with { Position = position.ToArray() } : point;

    private static IReadOnlyList<EditOp> FoldObjectEdits(IReadOnlyList<EditOp> edits)
    {
        var replay = new LevelState();
        var stack = new EditStack(replay);
        var placed = new List<(int Id, PlaceObject Spec)>();
        var hiddenChildren = new Dictionary<int, IReadOnlyList<string>>();
        var nextId = 0;

        foreach (var op in edits)
        {
            switch (op.OpType)
            {
                case PlaceObject.OpType:
                    var spec = PlaceObject.FromEditOp(op);
                    var id = spec.PlacementId ?? nextId;
                    nextId = id + spec.Attachments.Count + 1;
                    placed.Add((id, spec));
                    stack.Apply(op);
                    break;
                case MoveObject.OpType:
                case RemoveObject.OpType:
                    if (!op.Target.StartsWith("placement:", StringComparison.Ordinal))
                    {
                        break;
                    }

                    if (op.OpType == MoveObject.OpType)
                    {
                        var move = MoveObject.FromEditOp(op);
                        hiddenChildren[move.Target.PlacementId] = move.HiddenChildren;
                    }

                    stack.Apply(op);
                    break;
            }
        }

        var folded = new List<EditOp>();
        foreach (var (id, spec) in placed)
        {
            var target = ObjectTarget.FromPlacementId(id);
            if (replay.GetObject(target) is not { Removed: false, Transform: { } transform } owner)
            {
                continue;
            }

            var attachments = new List<ObjectAttachmentSpec>();
            for (var i = 0; i < spec.Attachments.Count; i++)
            {
                var original = spec.Attachments[i];
                if (replay.GetObject(ObjectTarget.FromPlacementId(id + i + 1)) is { Removed: false } child)
                {
                    attachments.Add(new ObjectAttachmentSpec(original.Name, original.CatalogId, child.LocalTransform ?? original.LocalTransform, child.Hidden));
                }
            }

            folded.Add(new PlaceObject(spec.CatalogId, transform.Position, transform.Rotation, transform.Scale, owner.Hidden, attachments, id).ToEditOp());
            if (hiddenChildren.TryGetValue(id, out var hidden) && hidden.Count > 0)
            {
                folded.Add(new MoveObject(target, transform, hidden).ToEditOp());
            }
        }

        return folded;
    }
}
