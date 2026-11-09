using System.Collections.Generic;

namespace MegabonkLevels;

// See "Cell-change log" in docs/development.md.
public sealed class CellChangeTracker
{
    public const uint PlayerId = uint.MaxValue;

    private readonly Dictionary<uint, (GridCell Cell, int Level)> _last = new();

    public bool Changed(uint id, GridCell cell, int level)
    {
        if (_last.TryGetValue(id, out var previous) && previous.Cell.Equals(cell) && previous.Level == level)
        {
            return false;
        }

        _last[id] = (cell, level);
        return true;
    }

    public void Reset() => _last.Clear();
}
