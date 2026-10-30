using System;
using System.Linq;

namespace MegabonkLevels;

// A level's music names either a pack clip or a discovered runtime filename.
public readonly record struct LevelMusicReference(string Pack, string Asset)
{
    public bool IsRuntime => Pack == null;

    public static bool TryParse(string value, out LevelMusicReference reference)
    {
        reference = default;
        if (value != null && value.StartsWith("track:", StringComparison.Ordinal))
        {
            var name = value.Substring(6);
            if (string.IsNullOrWhiteSpace(name) || name.IndexOfAny(new[] { '/', '\\', ':' }) >= 0 || name.Any(char.IsControl))
            {
                return false;
            }

            reference = new LevelMusicReference(null, name);
            return true;
        }

        if (!CatalogId.TryParse(value, out var id, out _) || id.Namespace != CatalogNamespace.Bundle || id.Segments.Count != 2)
        {
            return false;
        }

        reference = new LevelMusicReference(id.Segments[0], id.Segments[1]);
        return true;
    }
}
