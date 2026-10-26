namespace MegabonkLevels;

public sealed class PaletteSearchInput
{
    public const int MaxLength = 128;

    private readonly TextFieldModel _field = new(MaxLength);

    public TextFieldModel Field => _field;
    public string Query => _field.Text;
    public int Caret => _field.Caret;
    public bool Focused { get; private set; }
    public bool CapturesKeyboard { get; private set; }

    public void Step(bool clicked, bool overSearch, bool escape, string text, bool controlHeld = false, CaretKeys keys = default)
    {
        CapturesKeyboard = Focused;
        if (clicked)
        {
            var wasFocused = Focused;
            Focused = overSearch;
            if (Focused && !wasFocused)
            {
                _field.Navigate(new CaretKeys(End: true));
            }
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

        if (_field.Type(text))
        {
            Focused = false;
            return;
        }

        _field.Navigate(keys);
    }

    public void Reset()
    {
        _field.Clear();
        Focused = false;
        CapturesKeyboard = false;
    }

    public void Blur()
    {
        Focused = false;
        CapturesKeyboard = true;
    }
}
