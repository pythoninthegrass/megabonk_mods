using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// Picks the character a mod-loaded run starts with; the id mirrors the game's ECharacter.TonyMcZoom.
public static class CharacterOverride
{
    public const int TonyMcZoomId = 13;
    public const int CalciumId = 1;

    public static string DisplayName(int id) => id switch
    {
        CalciumId => "Calcium",
        TonyMcZoomId => "Tony McZoom",
        _ => $"character {id}",
    };

    public static bool IsAllowed(int id) => id == CalciumId || id == TonyMcZoomId;

    // Maps a harness or settings name to a character id; null when the name is not an allowed character.
    public static int? TryParseName(string name)
    {
        return name?.Trim().ToLowerInvariant() switch
        {
            "calcium" => CalciumId,
            "tony" or "tonymczoom" => TonyMcZoomId,
            _ => null,
        };
    }

    // Returns a warning when the setter throws, so the run can still start with the game's default character.
    public static string TryApply(Action<int> setSelected, int id = TonyMcZoomId)
    {
        try
        {
            setSelected(id);
            return null;
        }
        catch (Exception ex)
        {
            return $"LevelLoader: could not select character {id}, run starts with the default character: {ex.Message}";
        }
    }
}

// With the dev flag on, a mod-loaded run skips the character screen and uses this character.
public static class DevCharacter
{
    // Returns null when the flag is off so the player goes through the screen.
    public static int? Resolve(bool devEnabled, string name)
    {
        if (!devEnabled)
        {
            return null;
        }

        if (string.IsNullOrWhiteSpace(name))
        {
            return CharacterOverride.TonyMcZoomId;
        }

        return CharacterOverride.TryParseName(name)
            ?? throw new ArgumentException($"'{name}' is not an allowed character (calcium, tonymczoom)");
    }
}

// Orders the character grid for a custom run: Calcium, then Tony McZoom, then the stock order.
public static class CharacterGridOrder
{
    public static IReadOnlyList<int> Pin(IReadOnlyList<int> stockIds)
    {
        var pinned = new[] { CharacterOverride.CalciumId, CharacterOverride.TonyMcZoomId }.Where(stockIds.Contains);
        return pinned.Concat(stockIds.Where(id => !CharacterOverride.IsAllowed(id))).ToList();
    }
}
