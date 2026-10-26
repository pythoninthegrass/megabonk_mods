using System;

namespace MegabonkLevels;

// Per-frame caret movement: repeat counts for the arrow keys and Delete, plus Home and End.
public readonly record struct CaretKeys(int Left = 0, int Right = 0, int Delete = 0, bool Home = false, bool End = false);

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

    public void Navigate(CaretKeys keys)
    {
        if (keys.Home)
        {
            Caret = 0;
        }

        Caret = Math.Clamp(Caret - keys.Left + keys.Right, 0, Text.Length);
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
}
