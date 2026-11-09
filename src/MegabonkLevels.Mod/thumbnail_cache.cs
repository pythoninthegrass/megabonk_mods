using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// Remembers one render per catalog id; a failed render is stored as null so it is not retried.
public sealed class ThumbnailCache<T> where T : class
{
    private readonly Dictionary<CatalogId, T> _items = new();

    public int Count => _items.Count;

    public bool TryGet(CatalogId id, out T value) => _items.TryGetValue(id, out value);

    public T GetOrRender(CatalogId id, Func<CatalogId, T> render)
    {
        if (!_items.TryGetValue(id, out var value))
        {
            value = render(id);
            _items[id] = value;
        }

        return value;
    }

    public void Clear() => _items.Clear();
}
