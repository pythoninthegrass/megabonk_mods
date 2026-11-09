using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// The radio's songs; Next, Previous and Select move through them and wrap at the ends.
public sealed class RadioPlaylist
{
    private readonly IReadOnlyList<string> _clips;
    private int _index;
    private int _current = -1;

    public RadioPlaylist(IEnumerable<string> clipNames) : this(clipNames, preserveOrder: false)
    {
    }

    private RadioPlaylist(IEnumerable<string> clipNames, bool preserveOrder)
    {
        var distinct = clipNames.Distinct();
        _clips = (preserveOrder ? distinct : distinct.OrderBy(name => name, StringComparer.Ordinal)).ToList();
    }

    public IReadOnlyList<string> Names => _clips;

    public int Count => _clips.Count;

    // The 1-based number of the clip last chosen, or 0 before any.
    public int CurrentNumber => _current + 1;

    public static RadioPlaylist PreserveOrder(IEnumerable<string> clipNames) => new(clipNames, preserveOrder: true);

    // Makes the next clip the one after `clip`, so the radio continues the playlist from the clip already playing; an unknown clip leaves the start unchanged.
    public void StartAfter(string clip)
    {
        var at = _clips.ToList().IndexOf(clip);
        if (at >= 0)
        {
            _current = at;
            _index = (at + 1) % _clips.Count;
        }
    }

    // A looping clip's playback position jumps back to the start when the clip ends; ordinary playback moves forward.
    public static bool LoopWrapped(float previousTime, float currentTime) => previousTime - currentTime > 1f;

    public string Peek() => _clips.Count == 0 ? null : _clips[_index % _clips.Count];

    public string Next()
    {
        if (_clips.Count == 0)
        {
            return null;
        }

        return Choose(_index % _clips.Count);
    }

    // Steps back from the clip last chosen; before any clip is chosen it starts at the last one.
    public string Previous() => _clips.Count == 0 ? null : Choose((_current < 0 ? _clips.Count - 1 : _current - 1 + _clips.Count) % _clips.Count);

    // Chooses the clip at a 1-based number; an out-of-range number returns null and changes nothing.
    public string Select(int number) => number >= 1 && number <= _clips.Count ? Choose(number - 1) : null;

    private string Choose(int at)
    {
        _current = at;
        _index = (at + 1) % _clips.Count;
        return _clips[at];
    }
}
