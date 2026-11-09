using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

public readonly record struct CustomMapEntry(string Path, string Title, string Description, EMap Map, IReadOnlyList<string> AllowedCharacters = null);

// Picks the levels the game's Map Selection screen lists beside the native maps: those with a title, described by mapDescription or else the banner description.
public static class CustomMapEntries
{
    public static IReadOnlyList<CustomMapEntry> From(IEnumerable<(string Path, LevelFile Level)> levels) =>
        levels
            .Where(l => !string.IsNullOrWhiteSpace(l.Level.Title))
            .Select(l => new CustomMapEntry(l.Path, l.Level.Title, l.Level.MapDescription ?? l.Level.Description ?? "", l.Level.Map, l.Level.AllowedCharacters))
            .OrderBy(e => e.Title, StringComparer.OrdinalIgnoreCase)
            .ToList();
}
