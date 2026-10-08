using System;

namespace MegabonkLevels;

// Picks the character a mod-loaded run starts with; the id mirrors the game's ECharacter.TonyMcZoom.
public static class CharacterOverride
{
    public const int TonyMcZoomId = 13;

    // Returns a warning when the setter throws, so the run can still start with the game's default character.
    public static string TryApply(Action<int> setSelected)
    {
        try
        {
            setSelected(TonyMcZoomId);
            return null;
        }
        catch (Exception ex)
        {
            return $"LevelLoader: could not select Tony McZoom, run starts with the default character: {ex.Message}";
        }
    }
}
