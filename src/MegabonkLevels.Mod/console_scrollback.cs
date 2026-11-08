using System;
using System.Collections.Generic;

namespace MegabonkLevels;

// Output lines the console has printed, newest at the end. The buffer is bounded; PageUp/PageDown move a viewport
// over it, and a viewport pinned below the bottom stays put while new lines arrive.
public sealed class ConsoleScrollback
{
    private readonly List<string> _lines = new();
    private readonly int _maxLines;
    private readonly int _viewport;
    private int _offset;

    public ConsoleScrollback(int maxLines, int viewportLines)
    {
        _maxLines = Math.Max(1, maxLines);
        _viewport = Math.Max(1, viewportLines);
    }

    public IReadOnlyList<string> Lines => _lines;

    public int Count => _lines.Count;

    // The viewport's lines: the tail of the buffer while following, or _offset lines back from the bottom once scrolled up.
    public IReadOnlyList<string> VisibleLines
    {
        get
        {
            var end = Math.Clamp(_lines.Count - _offset, 0, _lines.Count);
            var start = Math.Max(0, end - _viewport);
            return _lines.GetRange(start, end - start);
        }
    }

    // A multi-line reply becomes one scrollback line per non-empty line, with either newline spelling.
    public static IReadOnlyList<string> Split(string text)
    {
        if (string.IsNullOrEmpty(text))
        {
            return Array.Empty<string>();
        }

        var lines = new List<string>();
        foreach (var line in text.Replace("\r\n", "\n").Replace('\r', '\n').Split('\n'))
        {
            if (line.Length > 0)
            {
                lines.Add(line);
            }
        }

        return lines;
    }

    public void Append(string text)
    {
        var followed = _offset == 0;
        foreach (var line in Split(text))
        {
            _lines.Add(line);
        }

        if (_lines.Count > _maxLines)
        {
            _lines.RemoveRange(0, _lines.Count - _maxLines);
        }

        if (followed)
        {
            ScrollToBottom();
        }
        else
        {
            _offset = Math.Min(_offset, Math.Max(0, _lines.Count - _viewport));
        }
    }

    public void Clear()
    {
        _lines.Clear();
        _offset = 0;
    }

    // One PageUp scrolls a viewport; the top page may be partial when the last page was.
    public void PageUp() => _offset = Math.Min(_offset + _viewport, Math.Max(0, _lines.Count - _viewport));

    public void PageDown() => _offset = Math.Max(0, _offset - _viewport);

    public void ScrollToBottom() => _offset = 0;

    public void Follow() => ScrollToBottom();
}
