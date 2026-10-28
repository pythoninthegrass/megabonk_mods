using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// The radio's songs in clip-name order; Next advances through them and wraps.
public sealed class RadioPlaylist
{
    private readonly IReadOnlyList<string> _clips;
    private int _index;

    public RadioPlaylist(IEnumerable<string> clipNames)
    {
        _clips = clipNames.Distinct().OrderBy(name => name, StringComparer.Ordinal).ToList();
    }

    public string Next()
    {
        if (_clips.Count == 0)
        {
            return null;
        }

        var clip = _clips[_index % _clips.Count];
        _index = (_index + 1) % _clips.Count;
        return clip;
    }
}
