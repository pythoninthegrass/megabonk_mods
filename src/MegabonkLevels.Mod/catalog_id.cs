using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;

namespace MegabonkLevels;

public enum CatalogNamespace
{
    GameAsset,
    Bundle,
}

// Game-asset catalogId segments are a purely syntactic grammar here; this type does not know which
// map/stage/category names are real (that's TASK-004/005's catalog-building concern). Recommended
// game-asset shapes, cross-checked against TASK-002's confirmed DataManager/StageData/SpawnInteractables
// catalog organization (see docs/level-format.md):
//   {map}/stage{N}/randomMapObjects/{objectIndex}/{prefabIndex}
//   {map}/stage{N}/stageTilePrefabs/flat/{index}
//   {map}/stage{N}/stageTilePrefabs/specific/{index}
//   {map}/shrines/{index}
//   {map}/randomObjectsOverride/{groupIndex}/{prefabIndex}
//   interactable/chest
//   interactable/chestFree
//   interactable/boombox
//   interactable/rail/{index}
//   interactable/chargeShrine/{index}
//   interactable/greedShrine/{index}
// The game exposes these prefabs only as GameObject[] with no name field, so the final segment is
// typically a numeric index, not a human-readable name.
public readonly record struct CatalogId
{
    private static readonly Regex SegmentPattern = new("^[A-Za-z0-9_-]+$", RegexOptions.Compiled);
    private const string BundlePrefix = "bundle:";

    public CatalogNamespace Namespace { get; }
    public IReadOnlyList<string> Segments { get; }

    private CatalogId(CatalogNamespace ns, IReadOnlyList<string> segments)
    {
        Namespace = ns;
        Segments = segments;
    }

    public static CatalogId Parse(string raw)
    {
        if (!TryParse(raw, out var id, out var error))
        {
            throw new ArgumentException(error, nameof(raw));
        }

        return id;
    }

    public static bool TryParse(string raw, out CatalogId id, out string error)
    {
        id = default;

        if (string.IsNullOrWhiteSpace(raw))
        {
            error = "catalogId must not be empty or whitespace.";
            return false;
        }

        CatalogNamespace ns;
        string body;
        if (raw.StartsWith(BundlePrefix, StringComparison.Ordinal))
        {
            ns = CatalogNamespace.Bundle;
            body = raw.Substring(BundlePrefix.Length);
        }
        else if (raw.Contains(':'))
        {
            error = $"catalogId '{raw}' has an unknown namespace prefix; only 'bundle:' is recognized.";
            return false;
        }
        else
        {
            ns = CatalogNamespace.GameAsset;
            body = raw;
        }

        var segments = body.Split('/');
        foreach (var segment in segments)
        {
            if (segment.Length == 0)
            {
                error = $"catalogId '{raw}' contains an empty segment (check for leading/trailing or doubled '/').";
                return false;
            }

            if (!SegmentPattern.IsMatch(segment))
            {
                error = $"catalogId '{raw}' has invalid character(s) in segment '{segment}'; only letters, digits, '_', and '-' are allowed.";
                return false;
            }
        }

        if (segments.Length < 2)
        {
            error = $"catalogId '{raw}' has too few segments; must have at least 2, got {segments.Length}.";
            return false;
        }

        id = new CatalogId(ns, segments);
        error = null!;
        return true;
    }

    public string Serialize() => Namespace switch
    {
        CatalogNamespace.Bundle => BundlePrefix + string.Join("/", Segments),
        CatalogNamespace.GameAsset => string.Join("/", Segments),
        _ => throw new ArgumentException($"Unknown {nameof(CatalogNamespace)}: {Namespace}"),
    };

    // Segments is null for default(CatalogId) (e.g. the `out` parameter on a failed TryParse), so
    // equality/hashing must tolerate that rather than relying on IReadOnlyList<string>'s default
    // reference-based equality or crashing via SequenceEqual(null).
    public bool Equals(CatalogId other) =>
        Namespace == other.Namespace && (Segments is null || other.Segments is null
            ? ReferenceEquals(Segments, other.Segments)
            : Segments.SequenceEqual(other.Segments));

    public override int GetHashCode()
    {
        var hash = new HashCode();
        hash.Add(Namespace);
        if (Segments is not null)
        {
            foreach (var segment in Segments)
            {
                hash.Add(segment);
            }
        }

        return hash.ToHashCode();
    }
}
