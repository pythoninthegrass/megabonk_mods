using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// Up/Down recall of the lines typed this session; the newest entry sits at the end and Next() returns to a blank line.
public sealed class ConsoleHistory
{
    private readonly List<string> _entries = new();
    private readonly int _maxEntries;
    private int _cursor = -1;

    public ConsoleHistory(int maxEntries = 50)
    {
        _maxEntries = Math.Max(1, maxEntries);
    }

    public IReadOnlyList<string> Entries => _entries;

    public void Add(string line)
    {
        var text = line?.Trim();
        if (string.IsNullOrEmpty(text))
        {
            return;
        }

        if (_entries.Count > 0 && _entries[_entries.Count - 1] == text)
        {
            _cursor = -1;
            return;
        }

        _entries.Add(text);
        if (_entries.Count > _maxEntries)
        {
            _entries.RemoveAt(0);
        }

        _cursor = -1;
    }

    public string Previous()
    {
        if (_entries.Count == 0)
        {
            return "";
        }

        _cursor = _cursor < 0 ? _entries.Count - 1 : Math.Max(0, _cursor - 1);
        return _entries[_cursor];
    }

    public string Next()
    {
        if (_cursor < 0)
        {
            return "";
        }

        _cursor = _cursor >= _entries.Count - 1 ? -1 : _cursor + 1;
        return _cursor < 0 ? "" : _entries[_cursor];
    }

    public void Reset() => _cursor = -1;
}
