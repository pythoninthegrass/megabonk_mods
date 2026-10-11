using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace MegabonkLevels;

// Tracks the current edit list plus redo entries for editor save/undo/redo.
public sealed class EditHistory
{
    private readonly List<EditOp> _current;
    private readonly Stack<EditOp> _redo = new();

    public EditHistory(IReadOnlyList<EditOp> seed = null)
    {
        _current = seed != null ? new List<EditOp>(seed) : new List<EditOp>();
    }

    public IReadOnlyList<EditOp> CurrentEdits => _current;

    public bool CanUndo => _current.Count > 0;

    public bool CanRedo => _redo.Count > 0;

    public void Apply(EditOp op)
    {
        _current.Add(op);
        _redo.Clear();
    }

    public EditOp Undo()
    {
        if (_current.Count == 0)
        {
            return default;
        }

        var op = _current[_current.Count - 1];
        _current.RemoveAt(_current.Count - 1);
        _redo.Push(op);
        return op;
    }

    public EditOp Redo()
    {
        if (_redo.Count == 0)
        {
            return default;
        }

        var op = _redo.Pop();
        _current.Add(op);
        return op;
    }
}

public static class EditorFileNaming
{
    private const string LevelPrefix = "level";
    private const string Extension = ".mblevel.json";

    public static string NormalizeLevelFileName(string rawName)
    {
        var value = (rawName ?? "").Trim();
        if (value.EndsWith(Extension, StringComparison.OrdinalIgnoreCase))
        {
            value = value.Substring(0, value.Length - Extension.Length);
        }
        else if (value.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
        {
            value = value.Substring(0, value.Length - ".json".Length);
        }

        var chars = new List<char>(value.Length);
        var previousUnderscore = false;
        foreach (var c in value)
        {
            var allowed = char.IsLetterOrDigit(c) || c == '-' || c == '_';
            if (allowed)
            {
                chars.Add(c);
                previousUnderscore = false;
            }
            else if (!previousUnderscore)
            {
                chars.Add('_');
                previousUnderscore = true;
            }
        }

        value = new string(chars.ToArray()).Trim('_');

        if (value.Length == 0)
        {
            value = LevelPrefix;
        }

        return value + Extension;
    }

    public static IReadOnlyList<string> SortLevelNames(IEnumerable<string> names) =>
        names
            .OrderBy(n => n, StringComparer.OrdinalIgnoreCase)
            .ThenBy(n => n, StringComparer.Ordinal)
            .ToList();

    public static string StemForForm(string fileName, int maxChars)
    {
        var stem = fileName.EndsWith(Extension, StringComparison.OrdinalIgnoreCase)
            ? fileName.Substring(0, fileName.Length - Extension.Length)
            : fileName;
        return stem.Length <= maxChars ? stem : stem.Substring(0, maxChars);
    }
}

public static class EditorValidationTargets
{
    public static bool IsBossPortalName(string objectName)
    {
        if (string.IsNullOrWhiteSpace(objectName))
        {
            return false;
        }

        var lower = objectName.ToLowerInvariant();
        return lower.Contains("portal") && lower.Contains("boss") && !lower.Contains("spawn");
    }
}

public static class EditorHotkeys
{
    public static bool CtrlChordReady(float ctrlHeldSince, float now, float thresholdSeconds) =>
        ctrlHeldSince >= 0f && now - ctrlHeldSince >= thresholdSeconds;
}

public static class EditorOverlayModel
{
    public static int SelectedIndexAfterScroll(int selectedIndex, int itemCount, float notches)
    {
        if (itemCount <= 0)
        {
            return 0;
        }

        return Math.Clamp(selectedIndex - Math.Sign(notches), 0, itemCount - 1);
    }

    public static int LoadListStart(int selectedIndex, int itemCount, int maxListed)
    {
        if (itemCount <= 0)
        {
            return 0;
        }

        var start = Math.Max(0, selectedIndex - maxListed / 2);
        if (start + maxListed > itemCount)
        {
            start = Math.Max(0, itemCount - maxListed);
        }

        return start;
    }

    public static int? LoadIndexAtRow(int selectedIndex, int itemCount, int maxListed, int row)
    {
        var start = LoadListStart(selectedIndex, itemCount, maxListed);
        var index = start + row;
        return index >= 0 && index < itemCount ? index : null;
    }
}

public static class EditorInputModel
{
    public static bool PlaceholderVisible(string text) => string.IsNullOrEmpty(text);
}

public enum EditorLoadGuardAction
{
    Warn,
    Load,
}

public readonly record struct EditorLoadGuardResult(EditorLoadGuardAction Action, bool Armed);

public static class EditorLoadGuard
{
    public static EditorLoadGuardResult NextPrompt(int currentEditsCount, int savedEditsCount, bool armed, bool requireConfirm)
    {
        var dirty = currentEditsCount != savedEditsCount;
        if (!dirty || !requireConfirm)
        {
            return new EditorLoadGuardResult(EditorLoadGuardAction.Load, false);
        }

        return armed
            ? new EditorLoadGuardResult(EditorLoadGuardAction.Load, false)
            : new EditorLoadGuardResult(EditorLoadGuardAction.Warn, true);
    }
}

public readonly record struct EditCommandPlan(EditOp OriginalOp, IReadOnlyList<EditOp> UndoOps, IReadOnlyList<EditOp> RedoOpsAfterUndo);

public static class EditCommandPlanner
{
    public static EditCommandPlan Plan(EditOp op, LevelState state, int nextPlacementId, TransformData? removeObjectFallback)
    {
        switch (op.OpType)
        {
            case SetTileHeight.OpType:
            {
                var typed = SetTileHeight.FromEditOp(op);
                return TilePlan(state.GetTile(typed.X, typed.Z), typed.X, typed.Z, op);
            }
            case SetTileSlope.OpType:
            {
                var typed = SetTileSlope.FromEditOp(op);
                return TilePlan(state.GetTile(typed.X, typed.Z), typed.X, typed.Z, op);
            }
            case AddTile.OpType:
            {
                var typed = AddTile.FromEditOp(op);
                return TilePlan(state.GetTile(typed.X, typed.Z), typed.X, typed.Z, op);
            }
            case RemoveTile.OpType:
            {
                var typed = RemoveTile.FromEditOp(op);
                return TilePlan(state.GetTile(typed.X, typed.Z), typed.X, typed.Z, op);
            }
            case PlaceObject.OpType:
            {
                var placed = ObjectTarget.FromPlacementId(nextPlacementId);
                var place = PlaceObject.FromEditOp(op);
                var transform = new TransformData(place.Position, place.Rotation, place.Scale);
                    return new EditCommandPlan(
                        OriginalOp: op,
                        UndoOps: new[] { new RemoveObject(placed).ToEditOp() },
                        RedoOpsAfterUndo: new[] { new MoveObject(placed, transform).ToEditOp() });
                }
            case MoveObject.OpType:
            {
                var typed = MoveObject.FromEditOp(op);
                var previous = state.GetObject(typed.Target);
                if (previous is { } old && old.Transform is { } oldTransform)
                {
                    return new EditCommandPlan(
                        OriginalOp: op,
                        UndoOps: new[] { new MoveObject(typed.Target, oldTransform).ToEditOp() },
                        RedoOpsAfterUndo: new[] { op });
                }

                if (previous is { } removed && removed.Removed)
                {
                    return new EditCommandPlan(
                        OriginalOp: op,
                        UndoOps: new[] { new RemoveObject(typed.Target).ToEditOp() },
                        RedoOpsAfterUndo: new[] { op });
                }

                return new EditCommandPlan(op, Array.Empty<EditOp>(), new[] { op });
            }
            case RemoveObject.OpType:
            {
                var typed = RemoveObject.FromEditOp(op);
                var previous = state.GetObject(typed.Target);
                if (previous is { } old && old.Removed)
                {
                    return new EditCommandPlan(op, Array.Empty<EditOp>(), new[] { op });
                }

                if (previous is { } existing && existing.Transform is { } transform)
                {
                    return new EditCommandPlan(
                        OriginalOp: op,
                        UndoOps: new[] { new MoveObject(typed.Target, transform).ToEditOp() },
                        RedoOpsAfterUndo: new[] { op });
                }

                if (removeObjectFallback is { } fallback)
                {
                    return new EditCommandPlan(
                        OriginalOp: op,
                        UndoOps: new[] { new MoveObject(typed.Target, fallback).ToEditOp() },
                        RedoOpsAfterUndo: new[] { op });
                }

                return new EditCommandPlan(op, Array.Empty<EditOp>(), new[] { op });
            }
            default:
                throw new ArgumentException($"Unknown opType: '{op.OpType}'.", nameof(op));
        }
    }

    private static EditCommandPlan TilePlan(TileState? previous, int x, int z, EditOp redo) =>
        previous is { } tile
            ? new EditCommandPlan(redo, TileUndo(x, z, tile), new[] { redo })
            : new EditCommandPlan(redo, new[] { new RemoveTile(x, z).ToEditOp() }, new[] { redo });

    private static IReadOnlyList<EditOp> TileUndo(int x, int z, TileState tile)
    {
        var undo = new List<EditOp> { new AddTile(x, z, tile.Height).ToEditOp() };
        if (tile.Slope != SlopeDirection.None)
        {
            undo.Add(new SetTileSlope(x, z, tile.Slope).ToEditOp());
        }

        return undo;
    }
}

// Pure tile-reset plan for in-place level load: given the generation baseline and the current state
// (with all edits applied), returns the live actions needed to restore every tile back to baseline.
public static class InPlaceLoadTileReset
{
    public static IReadOnlyList<LiveAction> ComputeTileResets(LevelState baseline, LevelState current)
    {
        var actions = new List<LiveAction>();
        foreach (var (cell, baseTile) in baseline.Tiles)
        {
            var curTile = current.GetTile(cell.X, cell.Z);
            if (curTile == null || curTile.Value != baseTile)
            {
                actions.Add(new LiveAction(LiveActionKind.SetTile, cell.X, cell.Z, baseTile, default, "", null));
            }
        }
        foreach (var (cell, _) in current.Tiles)
        {
            if (baseline.GetTile(cell.X, cell.Z) == null)
            {
                actions.Add(new LiveAction(LiveActionKind.RemoveTile, cell.X, cell.Z, null, default, "", null));
            }
        }
        return actions;
    }
}
