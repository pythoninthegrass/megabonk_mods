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
    private readonly int _wrapColumns;
    private int _offset;

    // wrapColumns is the row width in characters; longer lines are hard-wrapped into several rows as they are appended.
    public ConsoleScrollback(int maxLines, int viewportLines, int wrapColumns = int.MaxValue)
    {
        _maxLines = Math.Max(1, maxLines);
        _viewport = Math.Max(1, viewportLines);
        _wrapColumns = Math.Max(1, wrapColumns);
    }

    public IReadOnlyList<string> Lines => _lines;

    public int Count => _lines.Count;

    public int Viewport => _viewport;

    // Lines the viewport sits above the bottom; 0 while following.
    public int Offset => _offset;

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

    public static IReadOnlyList<string> Wrap(string line, int columns)
    {
        columns = Math.Max(1, columns);
        var rows = new List<string>();
        for (var start = 0; start < line.Length; start += columns)
        {
            rows.Add(line.Substring(start, Math.Min(columns, line.Length - start)));
        }

        return rows;
    }

    public void Append(string text)
    {
        var followed = _offset == 0;
        foreach (var line in Split(text))
        {
            _lines.AddRange(Wrap(line, _wrapColumns));
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

    // Positive moves toward older lines, negative toward newer, clamped to the buffer.
    public void ScrollBy(int lines) => _offset = Math.Clamp(_offset + lines, 0, Math.Max(0, _lines.Count - _viewport));

    public void PageDown() => _offset = Math.Max(0, _offset - _viewport);

    public void ScrollToBottom() => _offset = 0;

    public void Follow() => ScrollToBottom();
}
