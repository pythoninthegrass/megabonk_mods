using System;
using System.Collections.Generic;

namespace MegabonkLevels;

public enum LiveActionKind
{
    SetTile,
    RemoveTile,
    SpawnObject,
    MoveObject,
    RemoveObject,
}

// One step to run against the live game. Tile (for SetTile) is the resulting state after replaying
// every earlier op, so a slope edit after a height edit carries the height.
public readonly record struct LiveAction(
    LiveActionKind Kind,
    int X,
    int Z,
    TileState? Tile,
    ObjectTarget Target,
    string CatalogId,
    TransformData? Transform);

// Replays EditOps through the same EditStack the in-memory model uses, so op semantics (resulting tile
// state, monotonic placement ids) stay in one place, and flattens them into ordered live actions.
public static class LiveEditPlan
{
    public static IReadOnlyList<LiveAction> Build(IReadOnlyList<EditOp> edits)
    {
        var stack = new EditStack(new LevelState());
        var actions = new List<LiveAction>();
        var nextPlacementId = 0;

        foreach (var op in edits)
        {
            stack.Apply(op);
            actions.Add(ToAction(op, stack.State, ref nextPlacementId));
        }

        return actions;
    }

    // True when any action moves, adds or removes a tile, so the baked ground collision no longer matches the visuals.
    public static bool ChangesTerrain(IReadOnlyList<LiveAction> plan)
    {
        foreach (var action in plan)
        {
            if (action.Kind is LiveActionKind.SetTile or LiveActionKind.RemoveTile)
            {
                return true;
            }
        }

        return false;
    }

    private static LiveAction ToAction(EditOp op, LevelState state, ref int nextPlacementId)
    {
        switch (op.OpType)
        {
            case SetTileHeight.OpType:
            {
                var typed = SetTileHeight.FromEditOp(op);
                return SetTile(typed.X, typed.Z, state);
            }
            case SetTileSlope.OpType:
            {
                var typed = SetTileSlope.FromEditOp(op);
                return SetTile(typed.X, typed.Z, state);
            }
            case AddTile.OpType:
            {
                var typed = AddTile.FromEditOp(op);
                return SetTile(typed.X, typed.Z, state);
            }
            case RemoveTile.OpType:
            {
                var typed = RemoveTile.FromEditOp(op);
                return new LiveAction(LiveActionKind.RemoveTile, typed.X, typed.Z, null, default, "", null);
            }
            case PlaceObject.OpType:
            {
                var typed = PlaceObject.FromEditOp(op);
                var transform = new TransformData(typed.Position, typed.Rotation, typed.Scale);
                var target = ObjectTarget.FromPlacementId(nextPlacementId++);
                return new LiveAction(LiveActionKind.SpawnObject, 0, 0, null, target, typed.CatalogId, transform);
            }
            case MoveObject.OpType:
            {
                var typed = MoveObject.FromEditOp(op);
                return new LiveAction(LiveActionKind.MoveObject, 0, 0, null, typed.Target, "", typed.NewTransform);
            }
            case RemoveObject.OpType:
            {
                var typed = RemoveObject.FromEditOp(op);
                return new LiveAction(LiveActionKind.RemoveObject, 0, 0, null, typed.Target, "", null);
            }
            default:
                throw new ArgumentException($"Unknown opType: '{op.OpType}'.", nameof(op));
        }
    }

    private static LiveAction SetTile(int x, int z, LevelState state) =>
        new(LiveActionKind.SetTile, x, z, state.GetTile(x, z), default, "", null);
}
