namespace MegabonkLevels;

// Remembers the HUD's alpha across a hide so a show restores whatever was there before.
public sealed class HudVisibility
{
    private float? _savedAlpha;

    public bool Hidden => _savedAlpha.HasValue;

    public float Hide(float currentAlpha)
    {
        _savedAlpha ??= currentAlpha;
        return 0f;
    }

    public float? Show()
    {
        var saved = _savedAlpha;
        _savedAlpha = null;
        return saved;
    }
}
