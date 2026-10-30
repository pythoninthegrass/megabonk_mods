using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// The radio's songs; Next advances through them and wraps.
public sealed class RadioPlaylist
{
    private readonly IReadOnlyList<string> _clips;
    private int _index;

    public RadioPlaylist(IEnumerable<string> clipNames) : this(clipNames, preserveOrder: false)
    {
    }

    private RadioPlaylist(IEnumerable<string> clipNames, bool preserveOrder)
    {
        var distinct = clipNames.Distinct();
        _clips = (preserveOrder ? distinct : distinct.OrderBy(name => name, StringComparer.Ordinal)).ToList();
    }

    public static RadioPlaylist PreserveOrder(IEnumerable<string> clipNames) => new(clipNames, preserveOrder: true);

    // Makes the next clip the one after `clip`, so the radio continues the playlist from the clip already playing; an unknown clip leaves the start unchanged.
    public void StartAfter(string clip)
    {
        var at = _clips.ToList().IndexOf(clip);
        if (at >= 0)
        {
            _index = (at + 1) % _clips.Count;
        }
    }

    // A looping clip's playback position jumps back to the start when the clip ends; ordinary playback moves forward.
    public static bool LoopWrapped(float previousTime, float currentTime) => previousTime - currentTime > 1f;

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
