using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// Assigns the "{category}:{index}" genIds from docs/runtime-map-structure.md. Order is the order the
// game populated the source list, never a sorted order, so the same seed yields the same ids.
public static class GenIdAssigner
{
    public static IReadOnlyList<(string GenId, T Item)> Assign<T>(string category, IEnumerable<T> source)
    {
        if (string.IsNullOrWhiteSpace(category))
        {
            throw new ArgumentException("category must not be null or whitespace.", nameof(category));
        }

        return source.Select((item, i) => ($"{category}:{i:D4}", item)).ToList();
    }

    public static Dictionary<string, T> Index<T>(IReadOnlyDictionary<string, IReadOnlyList<T>> sourcesByCategory)
    {
        var index = new Dictionary<string, T>();
        foreach (var (category, source) in sourcesByCategory)
        {
            foreach (var (genId, item) in Assign(category, source))
            {
                index[genId] = item;
            }
        }

        return index;
    }
}
