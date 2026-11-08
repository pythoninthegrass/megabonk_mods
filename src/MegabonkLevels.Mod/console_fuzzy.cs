using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// One entry that passed the query: its index in the searched list and the character positions to highlight.
public readonly record struct ConsoleFuzzyHit(int Index, IReadOnlyList<int> Positions);

// fzf's extended-search syntax over a list of lines. See "Console history search" in docs/development.md.
public static class ConsoleFuzzy
{
    public static ConsoleFuzzyQuery Parse(string query) => ConsoleFuzzyQuery.Parse(query ?? "");

    // Chronological order is kept, not relevance order, as fzf does with --no-sort.
    public static IReadOnlyList<ConsoleFuzzyHit> Filter(IReadOnlyList<string> entries, string query)
    {
        var parsed = Parse(query);
        var hits = new List<ConsoleFuzzyHit>();
        for (var i = 0; i < entries.Count; i++)
        {
            if (parsed.Match(entries[i]) is { } positions)
            {
                hits.Add(new ConsoleFuzzyHit(i, positions));
            }
        }

        return hits;
    }
}

public sealed class ConsoleFuzzyQuery
{
    // Space-separated terms are ANDed; terms joined by a lone | form one group where any term may match.
    private readonly List<List<Term>> _groups;
    private readonly StringComparison _comparison;

    private ConsoleFuzzyQuery(List<List<Term>> groups, StringComparison comparison)
    {
        _groups = groups;
        _comparison = comparison;
    }

    // Smart-case: the whole query is case-sensitive once it holds an uppercase letter.
    public static ConsoleFuzzyQuery Parse(string query)
    {
        var comparison = query.Any(char.IsUpper) ? StringComparison.Ordinal : StringComparison.OrdinalIgnoreCase;
        var groups = new List<List<Term>>();
        var joinNext = false;
        foreach (var token in query.Split((char[])null, StringSplitOptions.RemoveEmptyEntries))
        {
            if (token == "|")
            {
                joinNext = groups.Count > 0;
            }
            else if (Term.Parse(token) is { } term)
            {
                if (joinNext)
                {
                    groups[groups.Count - 1].Add(term);
                }
                else
                {
                    groups.Add(new List<Term> { term });
                }

                joinNext = false;
            }
        }

        return new ConsoleFuzzyQuery(groups, comparison);
    }

    // Null when the text does not match; otherwise the sorted positions of every matched character.
    public IReadOnlyList<int> Match(string text)
    {
        if (_groups.Count == 0)
        {
            return Array.Empty<int>();
        }

        var positions = new SortedSet<int>();
        foreach (var group in _groups)
        {
            var found = false;
            foreach (var term in group)
            {
                if (term.Match(text, _comparison) is { } matched)
                {
                    positions.UnionWith(matched);
                    found = true;
                    break;
                }
            }

            if (!found)
            {
                return null;
            }
        }

        return positions.ToArray();
    }

    private sealed class Term
    {
        private Term(string text, bool exact, bool prefix, bool suffix, bool inverse)
        {
            Text = text;
            Exact = exact;
            Prefix = prefix;
            Suffix = suffix;
            Inverse = inverse;
        }

        private string Text { get; }
        private bool Exact { get; }
        private bool Prefix { get; }
        private bool Suffix { get; }
        private bool Inverse { get; }

        public static Term Parse(string token)
        {
            var inverse = token.StartsWith('!');
            if (inverse)
            {
                token = token.Substring(1);
            }

            var exact = inverse || token.StartsWith('\'');
            if (token.StartsWith('\''))
            {
                token = token.Substring(1);
            }

            var prefix = token.StartsWith('^');
            if (prefix)
            {
                token = token.Substring(1);
            }

            var suffix = token.EndsWith('$');
            if (suffix)
            {
                token = token.Substring(0, token.Length - 1);
            }

            return token.Length == 0 ? null : new Term(token, exact || prefix || suffix, prefix, suffix, inverse);
        }

        public IReadOnlyList<int> Match(string text, StringComparison comparison)
        {
            var at = Exact ? ExactIndex(text, comparison) : -1;
            if (Inverse)
            {
                return at < 0 ? Array.Empty<int>() : null;
            }

            if (Exact)
            {
                return at < 0 ? null : Enumerable.Range(at, Text.Length).ToArray();
            }

            return FuzzyPositions(text, comparison);
        }

        private int ExactIndex(string text, StringComparison comparison)
        {
            if (Prefix && Suffix)
            {
                return string.Equals(text, Text, comparison) ? 0 : -1;
            }

            if (Prefix)
            {
                return text.StartsWith(Text, comparison) ? 0 : -1;
            }

            if (Suffix)
            {
                return text.EndsWith(Text, comparison) ? text.Length - Text.Length : -1;
            }

            return text.IndexOf(Text, comparison);
        }

        // Leftmost subsequence match, then tightened from the right so the span is the shortest ending there.
        private int[] FuzzyPositions(string text, StringComparison comparison)
        {
            var end = -1;
            foreach (var c in Text)
            {
                end = text.IndexOf(c.ToString(), end + 1, comparison);
                if (end < 0)
                {
                    return null;
                }
            }

            var positions = new int[Text.Length];
            var at = end;
            for (var i = Text.Length - 1; i >= 0; i--)
            {
                at = text.LastIndexOf(Text[i].ToString(), at, at + 1, comparison);
                positions[i] = at;
                at--;
            }

            return positions;
        }
    }
}
