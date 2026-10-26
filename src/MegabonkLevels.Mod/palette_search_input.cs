namespace MegabonkLevels;

public sealed class PaletteSearchInput
{
    public const int MaxLength = 128;

    public string Query { get; private set; } = "";
    public bool Focused { get; private set; }
    public bool CapturesKeyboard { get; private set; }

    public void Step(bool clicked, bool overSearch, bool escape, string text, bool controlHeld = false)
    {
        CapturesKeyboard = Focused;
        if (clicked)
        {
            Focused = overSearch;
        }

        CapturesKeyboard |= Focused;
        if (escape)
        {
            Focused = false;
        }

        if (!Focused || controlHeld)
        {
            return;
        }

        foreach (var c in text)
        {
            if (c == '\b' && Query.Length > 0)
            {
                Query = Query.Substring(0, Query.Length - 1);
            }
            else if (c == '\r' || c == '\n')
            {
                Focused = false;
                break;
            }
            else if (!char.IsControl(c) && Query.Length < MaxLength)
            {
                Query += c;
            }
        }
    }

    public void Reset()
    {
        Query = "";
        Focused = false;
        CapturesKeyboard = false;
    }
}
