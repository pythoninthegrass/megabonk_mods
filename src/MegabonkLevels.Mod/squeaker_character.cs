using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// Squeaker's data: the Tiny target stat rows, the collider and the pack assets; the values are documented in docs/characters.md.
public static class SqueakerCharacter
{
    public const int Id = 21;
    public const string DisplayName = "Squeaker";
    public const string ModelCatalogId = "bundle:squeaker/Squeaker";
    public const string CookieCatalogId = "bundle:squeaker/StaleCookie";
    public const int EvasionStat = 5;
    public const float ColliderHeight = 2.9f;
    public const float ColliderWidth = 0.5f;
    public const string PassiveName = "Tiny Target";
    public const string WeaponName = "Stale Cookie";
    public const string WeaponDescription = "Throws stale cookies that bounce off enemies";

    private const float MaxHealthPenalty = 30f;
    private const float EvasionBonus = 0.25f;

    public static readonly IReadOnlyList<StatModifierRow> TinyTargetModifiers = new[]
    {
        new StatModifierRow(FallDamagePolicy.MaxHealthStat, FallDamagePolicy.Flat, -MaxHealthPenalty),
        new StatModifierRow(EvasionStat, FallDamagePolicy.Flat, EvasionBonus),
    };

    public static bool UsesCookieProjectile(int characterId) => characterId == Id;

    // The game stores evasion as v / (v + 1) * 0.999, so a flat 0.25 reads as 20%.
    public static int EvasionPercent(float flat) => (int)System.Math.Round(flat / (flat + 1f) * 0.999f * 100f);

    public static string PassiveDescription =>
        $"Smaller hitbox and {EvasionPercent(EvasionBonus)}% evasion, but {MaxHealthPenalty:0} max HP less.";
}

// Decides when the mod's characters are added to the game's tables; ids past the stock ECharacter range belong to the mod.
public static class ModCharacterRegistration
{
    private const int LastStockId = 20;

    public static bool IsModCharacter(int id) => id > LastStockId;

    public static bool ShouldAppend(IEnumerable<int> registeredIds, int id) => !registeredIds.Contains(id);

    public static bool NeedsSkinSeed(IEnumerable<int> seededIds, int id) => !seededIds.Contains(id);
}

// Keeps the saved preference naming a character the stock game can resolve.
public static class SelectedCharacterGuard
{
    // The stock character to write back when the current selection is a mod character; null when nothing needs restoring.
    public static int? RestoreTarget(int current, int? saved)
    {
        if (!ModCharacterRegistration.IsModCharacter(current))
        {
            return null;
        }

        return saved is { } id && !ModCharacterRegistration.IsModCharacter(id) ? id : CharacterOverride.CalciumId;
    }
}
