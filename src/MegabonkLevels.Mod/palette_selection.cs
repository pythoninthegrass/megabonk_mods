using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// The palette's entry list and the single selected catalogId that the placement tool reads.
public sealed class PaletteSelection
{
    private IReadOnlyList<PaletteEntry> _entries = Array.Empty<PaletteEntry>();

    public IReadOnlyList<PaletteEntry> Entries => _entries;

    public CatalogId? Current { get; private set; }

    public event Action<CatalogId?> Changed;

    public void Replace(IReadOnlyList<PaletteEntry> entries)
    {
        _entries = entries;
        if (Current is { } current && !entries.Any(e => e.Id.Equals(current)))
        {
            Clear();
        }
    }

    public void Select(CatalogId id)
    {
        if (!_entries.Any(e => e.Id.Equals(id)))
        {
            throw new ArgumentException($"'{id.Serialize()}' is not in the palette.", nameof(id));
        }

        Current = id;
        Changed?.Invoke(id);
    }

    public void Clear()
    {
        if (Current is null)
        {
            return;
        }

        Current = null;
        Changed?.Invoke(null);
    }
}
