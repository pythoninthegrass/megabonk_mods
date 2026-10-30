using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// Applies TASK-003.02 EditOps to a LevelState with undo/redo. Every op's inverse is built from the
// LevelState value it overwrites (captured before mutation), so undo always restores the exact prior
// record — including "no record existed", which undo reverts to by deleting the entry rather than
// writing a synthesized default.
public sealed class EditStack
{
    private readonly record struct UndoEntry(Action Undo, Action Redo);

    private readonly LevelState _state;
    private readonly Stack<UndoEntry> _undoStack = new();
    private readonly Stack<UndoEntry> _redoStack = new();

    public EditStack(LevelState state)
    {
        _state = state;
    }

    public LevelState State => _state;

    public bool CanUndo => _undoStack.Count > 0;

    public bool CanRedo => _redoStack.Count > 0;

    public void Apply(EditOp op)
    {
        var entry = BuildEntry(op);
        entry.Redo();
        _undoStack.Push(entry);
        _redoStack.Clear();
    }

    public bool Undo()
    {
        if (_undoStack.Count == 0)
        {
            return false;
        }

        var entry = _undoStack.Pop();
        entry.Undo();
        _redoStack.Push(entry);
        return true;
    }

    public bool Redo()
    {
        if (_redoStack.Count == 0)
        {
            return false;
        }

        var entry = _redoStack.Pop();
        entry.Redo();
        _undoStack.Push(entry);
        return true;
    }

    private UndoEntry BuildEntry(EditOp op) => op.OpType switch
    {
        SetTileHeight.OpType => BuildSetTileHeight(SetTileHeight.FromEditOp(op)),
        SetTileSlope.OpType => BuildSetTileSlope(SetTileSlope.FromEditOp(op)),
        AddTile.OpType => BuildAddTile(AddTile.FromEditOp(op)),
        RemoveTile.OpType => BuildRemoveTile(RemoveTile.FromEditOp(op)),
        PlaceObject.OpType => BuildPlaceObject(PlaceObject.FromEditOp(op)),
        MoveObject.OpType => BuildMoveObject(MoveObject.FromEditOp(op)),
        RemoveObject.OpType => BuildRemoveObject(RemoveObject.FromEditOp(op)),
        _ => throw new ArgumentException($"Unknown opType: '{op.OpType}'.", nameof(op)),
    };

    private UndoEntry BuildSetTileHeight(SetTileHeight typed)
    {
        var previous = _state.GetTile(typed.X, typed.Z);
        var slope = previous?.Slope ?? SlopeDirection.None;
        return new UndoEntry(
            Undo: () => RestoreTile(typed.X, typed.Z, previous),
            Redo: () => _state.SetTile(typed.X, typed.Z, new TileState(typed.Height, slope)));
    }

    private UndoEntry BuildSetTileSlope(SetTileSlope typed)
    {
        var previous = _state.GetTile(typed.X, typed.Z);
        var height = previous?.Height ?? 0;
        return new UndoEntry(
            Undo: () => RestoreTile(typed.X, typed.Z, previous),
            Redo: () => _state.SetTile(typed.X, typed.Z, new TileState(height, typed.Direction)));
    }

    private UndoEntry BuildAddTile(AddTile typed)
    {
        var previous = _state.GetTile(typed.X, typed.Z);
        return new UndoEntry(
            Undo: () => RestoreTile(typed.X, typed.Z, previous),
            Redo: () => _state.SetTile(typed.X, typed.Z, new TileState(typed.Height, SlopeDirection.None)));
    }

    private UndoEntry BuildRemoveTile(RemoveTile typed)
    {
        var previous = _state.GetTile(typed.X, typed.Z);
        return new UndoEntry(
            Undo: () => RestoreTile(typed.X, typed.Z, previous),
            Redo: () => _state.RemoveTile(typed.X, typed.Z));
    }

    private void RestoreTile(int x, int z, TileState? previous)
    {
        if (previous is { } value)
        {
            _state.SetTile(x, z, value);
        }
        else
        {
            _state.RemoveTile(x, z);
        }
    }

    private UndoEntry BuildPlaceObject(PlaceObject typed)
    {
        var target = _state.AllocatePlacementId(typed.PlacementId, typed.Attachments.Count + 1);
        var transform = new TransformData(typed.Position, typed.Rotation, typed.Scale);
        var children = new List<(ObjectTarget Target, ObjectState State)>();
        foreach (var child in typed.Attachments)
        {
            children.Add((ObjectTarget.FromPlacementId(target.PlacementId + children.Count + 1), new ObjectState(false, child.CatalogId,
                AttachmentTransform.ToWorld(transform, child.LocalTransform), target, child.LocalTransform, child.Hidden)));
        }
        return new UndoEntry(
            Undo: () =>
            {
                foreach (var child in children)
                {
                    _state.RemoveObject(child.Target);
                }
                _state.RemoveObject(target);
            },
            Redo: () =>
            {
                _state.SetObject(target, new ObjectState(false, typed.CatalogId, transform, Hidden: typed.Hidden));
                foreach (var child in children)
                {
                    _state.SetObject(child.Target, child.State);
                }
            });
    }

    private UndoEntry BuildMoveObject(MoveObject typed)
    {
        var previous = _state.GetObject(typed.Target);
        var catalogId = previous?.CatalogId ?? "";
        var next = (previous ?? new ObjectState(false, catalogId, null)) with { Removed = false, Transform = typed.NewTransform };
        if (next.Owner is { } owner && _state.GetObject(owner)?.Transform is { } ownerTransform)
        {
            next = next with { LocalTransform = AttachmentTransform.ToLocal(ownerTransform, typed.NewTransform) };
        }
        return new UndoEntry(
            Undo: () => RestoreObject(typed.Target, previous),
            Redo: () =>
            {
                _state.SetObject(typed.Target, next);
                _state.RefreshAttachments(typed.Target);
            });
    }

    private UndoEntry BuildRemoveObject(RemoveObject typed)
    {
        var previous = _state.GetObject(typed.Target);
        return new UndoEntry(
            Undo: () => RestoreObject(typed.Target, previous),
            Redo: () => _state.SetObject(typed.Target, (previous ?? new ObjectState(false, "", null)) with { Removed = true }));
    }

    private void RestoreObject(ObjectTarget target, ObjectState? previous)
    {
        if (previous is { } value)
        {
            _state.SetObject(target, value);
            _state.RefreshAttachments(target);
        }
        else
        {
            _state.RemoveObject(target);
        }
    }
}
