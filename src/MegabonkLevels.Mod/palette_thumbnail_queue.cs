using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// Hands out catalog ids to render thumbnails for, a few per call, so opening the palette or turning a page
// never pays for every prefab in one frame. Ids already rendered are visited but do not spend the budget.
public sealed class PaletteThumbnailQueue
{
    private readonly List<CatalogId> _ids = new();
    private int _cursor;

    public PaletteThumbnailQueue(int budget = 4) => Budget = budget;

    public int Budget { get; }

    public bool IsEmpty => _cursor >= _ids.Count;

    public int PendingCount => Math.Max(0, _ids.Count - _cursor);

    // Asks for a set of ids, duplicates dropped, and starts again from the first of them so the ids the
    // caller cares about most (the visible page) are the first ones handed out.
    public void Request(IReadOnlyList<CatalogId> ids)
    {
        _ids.Clear();
        var seen = new HashSet<CatalogId>();
        foreach (var id in ids)
        {
            if (seen.Add(id))
            {
                _ids.Add(id);
            }
        }

        _cursor = 0;
    }

    // Renders up to Budget pending entries. render returns false for an id that needed no work, such as one
    // already in the thumbnail cache; those are skipped without spending the budget. Returns how many rendered.
    public int Step(Func<CatalogId, bool> render)
    {
        var rendered = 0;
        while (_cursor < _ids.Count && rendered < Budget)
        {
            if (render(_ids[_cursor]))
            {
                rendered++;
            }

            _cursor++;
        }

        return rendered;
    }
}
