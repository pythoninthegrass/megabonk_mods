using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// The state behind Ctrl-R history search: the matching rows (newest first, so row 0 sits next to the prompt), a clamped
// selection and the scroll window that keeps it visible.
public sealed class ConsoleFinder
{
    public const string MatchColor = "#FFD24A";

    private readonly IReadOnlyList<string> _entries;
    private string _query = "";
    private int _top;

    public ConsoleFinder(IReadOnlyList<string> entries)
    {
        _entries = entries.ToArray();
        Rows = Search("");
    }

    public IReadOnlyList<ConsoleFuzzyHit> Rows { get; private set; }

    public int Selected { get; private set; }

    public int Total => _entries.Count;

    public string Info => $"{Rows.Count}/{Total}";

    public string SelectedEntry => Rows.Count == 0 ? null : RowText(Selected);

    public string RowText(int row) => _entries[Rows[row].Index];

    public void SetQuery(string query)
    {
        if (query == _query)
        {
            return;
        }

        _query = query;
        Rows = Search(query);
        Selected = 0;
    }

    public void Move(int delta) => Selected = Rows.Count == 0 ? 0 : Math.Clamp(Selected + delta, 0, Rows.Count - 1);

    // First visible row for a viewport of this many rows, scrolled the least that keeps the selection in view.
    public int Window(int viewportRows)
    {
        viewportRows = Math.Max(1, viewportRows);
        _top = Math.Min(_top, Math.Max(0, Rows.Count - viewportRows));
        if (Selected < _top)
        {
            _top = Selected;
        }
        else if (Selected >= _top + viewportRows)
        {
            _top = Selected - viewportRows + 1;
        }

        return _top;
    }

    // TextMeshPro rich text for one list row: a gutter marker, and the matched characters in the highlight colour.
    public static string RowMarkup(string entry, IReadOnlyList<int> positions, bool selected)
    {
        var matched = new HashSet<int>(positions);
        var text = new System.Text.StringBuilder(selected ? "> " : "  ");
        for (var i = 0; i < entry.Length; i++)
        {
            var glyph = entry[i] == '<' ? "<noparse><</noparse>" : entry[i].ToString();
            text.Append(matched.Contains(i) ? $"<color={MatchColor}>{glyph}</color>" : glyph);
        }

        return text.ToString();
    }

    private IReadOnlyList<ConsoleFuzzyHit> Search(string query) =>
        ConsoleFuzzy.Filter(_entries, query).Reverse().ToList();
}
