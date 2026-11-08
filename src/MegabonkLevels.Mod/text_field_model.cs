using System;

namespace MegabonkLevels;

// Per-frame caret movement: repeat counts for the arrow keys, word jumps and Delete, plus Home and End.
public readonly record struct CaretKeys(int Left = 0, int Right = 0, int Delete = 0, bool Home = false, bool End = false, int WordLeft = 0, int WordRight = 0);

// Single-line text with a caret, independent of Unity.
public sealed class TextFieldModel
{
    private readonly int _maxLength;

    public TextFieldModel(int maxLength)
    {
        _maxLength = maxLength;
    }

    public string Text { get; private set; } = "";
    public int Caret { get; private set; }

    public void Set(string text)
    {
        Text = text.Length > _maxLength ? text.Substring(0, _maxLength) : text;
        Caret = Text.Length;
    }

    public void Set(string text, int caret)
    {
        Set(text);
        Caret = Math.Clamp(caret, 0, Text.Length);
    }

    public void Clear() => Set("");

    // Returns true when Enter was typed; text after it is dropped.
    public bool Type(string input)
    {
        foreach (var c in input)
        {
            if (c == '\b')
            {
                if (Caret > 0)
                {
                    Text = Text.Remove(Caret - 1, 1);
                    Caret--;
                }
            }
            else if (c == '\r' || c == '\n')
            {
                return true;
            }
            else if (!char.IsControl(c) && Text.Length < _maxLength)
            {
                Text = Text.Insert(Caret, c.ToString());
                Caret++;
            }
        }

        return false;
    }

    // Ctrl-W: removes the whitespace-delimited word before the caret, and any spaces between it and the caret.
    public void DeleteWordLeft()
    {
        var start = WordStartLeft(Caret);
        Text = Text.Remove(start, Caret - start);
        Caret = start;
    }

    // Ctrl-U: removes everything before the caret.
    public void DeleteToStart()
    {
        Text = Text.Substring(Caret);
        Caret = 0;
    }

    // Ctrl-K: removes everything after the caret.
    public void DeleteToEnd() => Text = Text.Substring(0, Caret);

    public void Navigate(CaretKeys keys)
    {
        if (keys.Home)
        {
            Caret = 0;
        }

        Caret = Math.Clamp(Caret - keys.Left + keys.Right, 0, Text.Length);
        for (var i = 0; i < keys.WordLeft; i++)
        {
            Caret = WordStartLeft(Caret);
        }

        for (var i = 0; i < keys.WordRight; i++)
        {
            Caret = WordEndRight(Caret);
        }

        if (keys.End)
        {
            Caret = Text.Length;
        }

        var removed = Math.Min(keys.Delete, Text.Length - Caret);
        if (removed > 0)
        {
            Text = Text.Remove(Caret, removed);
        }
    }

    // Whitespace is the only word separator, like the shell's IFS.
    private int WordStartLeft(int from)
    {
        var start = from;
        while (start > 0 && char.IsWhiteSpace(Text[start - 1]))
        {
            start--;
        }

        while (start > 0 && !char.IsWhiteSpace(Text[start - 1]))
        {
            start--;
        }

        return start;
    }

    private int WordEndRight(int from)
    {
        var end = from;
        while (end < Text.Length && char.IsWhiteSpace(Text[end]))
        {
            end++;
        }

        while (end < Text.Length && !char.IsWhiteSpace(Text[end]))
        {
            end++;
        }

        return end;
    }
}
