using System;

namespace MegabonkLevels;

// Which slice of a long single-line text a fixed-width field shows so the caret stays visible.
public static class TextWindow
{
    public static int Start(int caret, int length, int capacity, int currentStart)
    {
        var start = Math.Min(currentStart, Math.Max(0, length - capacity));
        if (caret < start)
        {
            start = caret;
        }
        else if (caret > start + capacity)
        {
            start = caret - capacity;
        }

        return start;
    }

    public static string Visible(string text, int start, int capacity) =>
        text.Substring(start, Math.Min(capacity, text.Length - start));
}
