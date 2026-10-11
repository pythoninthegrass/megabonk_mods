using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// Editor-local undo/redo command stack. It keeps the serialized edit list for save while applying
// planned inverse/redo operations live.
public sealed class EditorEditSession
{
    private readonly EditHistory _history;
    private readonly Stack<EditCommandPlan> _undo = new();
    private readonly Stack<EditCommandPlan> _redo = new();

    public EditorEditSession(IReadOnlyList<EditOp> seed = null)
    {
        _history = new EditHistory(seed);
    }

    public IReadOnlyList<EditOp> CurrentEdits => _history.CurrentEdits;

    public bool CanUndo => _undo.Count > 0;

    public bool CanRedo => _redo.Count > 0;

    public bool Apply(EditCommandPlan plan, Func<EditOp, bool> applyLive)
    {
        if (!applyLive(plan.OriginalOp))
        {
            return false;
        }

        _history.Apply(plan.OriginalOp);
        _undo.Push(plan);
        _redo.Clear();
        return true;
    }

    public bool Undo(Func<EditOp, bool> applyLive)
    {
        if (_undo.Count == 0)
        {
            return false;
        }

        var plan = _undo.Peek();
        foreach (var op in plan.UndoOps)
        {
            if (!applyLive(op))
            {
                return false;
            }
        }

        _undo.Pop();
        _redo.Push(plan);
        _history.Undo();
        return true;
    }

    public bool Redo(Func<EditOp, bool> applyLive)
    {
        if (_redo.Count == 0)
        {
            return false;
        }

        var plan = _redo.Peek();
        foreach (var op in plan.RedoOpsAfterUndo)
        {
            if (!applyLive(op))
            {
                return false;
            }
        }

        _redo.Pop();
        _undo.Push(plan);
        _history.Redo();
        return true;
    }
}
