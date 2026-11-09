using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// A level's character rule from its allowedCharacters names; a null id set means anyone may play it.
public static class CharacterPolicy
{
    public static IReadOnlyList<int> AllowedIds(IReadOnlyList<string> names)
    {
        var ids = (names ?? new List<string>())
            .Select(CharacterOverride.TryParseName)
            .OfType<int>()
            .Distinct()
            .ToList();
        return ids.Count == 0 ? null : ids;
    }

    public static IReadOnlyList<string> UnknownNames(IReadOnlyList<string> names) =>
        (names ?? new List<string>()).Where(name => CharacterOverride.TryParseName(name) == null).ToList();

    public static bool Permits(IReadOnlyList<int> allowedIds, int id) => allowedIds == null || allowedIds.Contains(id);

    public static string Refusal(IReadOnlyList<int> allowedIds, string levelTitle)
    {
        var names = string.Join(" or ", allowedIds.Select(CharacterOverride.DisplayName));
        return $"Pick {names} for {levelTitle ?? "this level"}";
    }
}
