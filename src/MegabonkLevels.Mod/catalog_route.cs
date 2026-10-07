using System;

namespace MegabonkLevels;

public enum CatalogRouteKind
{
    RandomMapObject,
    FlatTilePrefab,
    SpecificTilePrefab,
    Shrine,
    Chest,
    ChestFree,
    Rail,
}

// A game-asset CatalogId broken into the typed path through the game's own prefab catalog. This type
// only decodes the id; walking DataManager/StageData with it happens in the Il2Cpp layer, so there is
// no duplicate prefab list.
public readonly record struct CatalogRoute(CatalogRouteKind Kind, EMap Map, int Stage, int Index, int SubIndex)
{
    public static CatalogRoute Parse(CatalogId id)
    {
        if (id.Namespace != CatalogNamespace.GameAsset)
        {
            throw new ArgumentException($"'{id.Serialize()}' is not a game-asset catalogId.", nameof(id));
        }

        var s = id.Segments;
        if (s.Count == 2 && s[0] == "interactable")
        {
            return s[1] switch
            {
                "chest" => new CatalogRoute(CatalogRouteKind.Chest, EMap.None, 0, 0, 0),
                "chestFree" => new CatalogRoute(CatalogRouteKind.ChestFree, EMap.None, 0, 0, 0),
                _ => throw Unresolvable(id),
            };
        }

        if (s.Count == 3 && s[0] == "interactable" && s[1] == "rail")
        {
            return new CatalogRoute(CatalogRouteKind.Rail, EMap.None, 0, Number(s[2], id), 0);
        }

        var map = ParseMap(s[0], id);
        if (s.Count == 3 && s[1] == "shrines")
        {
            return new CatalogRoute(CatalogRouteKind.Shrine, map, 0, Number(s[2], id), 0);
        }

        if (s.Count >= 4 && s[1].StartsWith("stage", StringComparison.Ordinal))
        {
            var stage = Number(s[1].Substring("stage".Length), id);
            if (s.Count == 5 && s[2] == "randomMapObjects")
            {
                return new CatalogRoute(CatalogRouteKind.RandomMapObject, map, stage, Number(s[3], id), Number(s[4], id));
            }

            if (s.Count == 5 && s[2] == "stageTilePrefabs" && s[3] == "flat")
            {
                return new CatalogRoute(CatalogRouteKind.FlatTilePrefab, map, stage, Number(s[4], id), 0);
            }

            if (s.Count == 5 && s[2] == "stageTilePrefabs" && s[3] == "specific")
            {
                return new CatalogRoute(CatalogRouteKind.SpecificTilePrefab, map, stage, Number(s[4], id), 0);
            }
        }

        throw Unresolvable(id);
    }

    private static EMap ParseMap(string segment, CatalogId id)
    {
        if (!Enum.TryParse<EMap>(segment, ignoreCase: true, out var map) || map == EMap.None || !Enum.IsDefined(typeof(EMap), map))
        {
            throw Unresolvable(id);
        }

        return map;
    }

    private static int Number(string segment, CatalogId id)
    {
        if (!int.TryParse(segment, out var value) || value < 0)
        {
            throw Unresolvable(id);
        }

        return value;
    }

    private static ArgumentException Unresolvable(CatalogId id) =>
        new($"catalogId '{id.Serialize()}' does not match a known game-asset catalog shape.", nameof(id));
}
