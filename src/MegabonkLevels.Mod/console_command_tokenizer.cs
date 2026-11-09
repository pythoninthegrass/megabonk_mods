using System;
using System.Collections.Generic;
using System.Text;

namespace MegabonkLevels;

// A console line split into a verb and its arguments; double quotes hold a run together across spaces.
// Tokens is null when the line cannot be split, and Error then carries the reply for the console.
public readonly record struct ConsoleTokens(IReadOnlyList<string> Tokens, string Error)
{
    public bool IsBlank => Tokens != null && Tokens.Count == 0;

    public string Verb => Tokens is { Count: > 0 } ? Tokens[0] : null;

    // The caller builds Tokens as a List, so the slice shares its buffer instead of copying.
    public IReadOnlyList<string> Arguments => Tokens is List<string> list and { Count: > 1 } ? list.GetRange(1, list.Count - 1) : Array.Empty<string>();
}

// The word being typed at the end of a line: where it starts, its text with quotes removed, and how many whole words precede it.
public readonly record struct ConsoleLastWord(int Start, string Text, int WordsBefore);

public static class ConsoleCommandTokenizer
{
    // Reads the line with Tokenize's quoting, so a word inside an unterminated quote still counts as the last word.
    public static ConsoleLastWord LastWord(string line)
    {
        var words = 0;
        var start = 0;
        var text = new StringBuilder();
        var inWord = false;
        var quoted = false;

        for (var i = 0; i < line.Length; i++)
        {
            var c = line[i];
            if (!quoted && char.IsWhiteSpace(c))
            {
                if (inWord)
                {
                    words++;
                    inWord = false;
                    text.Clear();
                }

                continue;
            }

            if (!inWord)
            {
                inWord = true;
                start = i;
            }

            if (c == '"')
            {
                quoted = !quoted;
            }
            else
            {
                text.Append(c);
            }
        }

        return inWord ? new ConsoleLastWord(start, text.ToString(), words) : new ConsoleLastWord(line.Length, "", words);
    }

    public static ConsoleTokens Tokenize(string line)
    {
        if (line == null || line.Trim().Length == 0)
        {
            return new ConsoleTokens(Array.Empty<string>(), null);
        }

        var tokens = new List<string>();
        var word = new StringBuilder();
        var started = false;
        var quoted = false;
        var index = 0;

        while (index < line.Length)
        {
            var c = line[index];

            if (!quoted && char.IsWhiteSpace(c))
            {
                if (started)
                {
                    tokens.Add(word.ToString());
                    word.Clear();
                    started = false;
                }

                index++;
                continue;
            }

            if (char.IsControl(c))
            {
                return new ConsoleTokens(null, "the line contains a control character");
            }

            started = true;
            if (c == '"')
            {
                quoted = !quoted;
            }
            else
            {
                word.Append(c);
            }

            index++;
        }

        if (quoted)
        {
            return new ConsoleTokens(null, "unterminated \"quote\"");
        }

        if (started)
        {
            tokens.Add(word.ToString());
        }

        return new ConsoleTokens(tokens, null);
    }
}
