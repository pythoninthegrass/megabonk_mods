using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

public enum ExtraShrineKind { Challenge, Magnet, Cursed, Greed, Balance, Moai, Charge }

// Placement policy for the extra shrines a level spawns each run: which kinds exist, and the
// keep-clear rules that keep a shrine's 12.5-unit charge sphere off other shrines and off the
// routes between the spawn portal, the boss portal and the final portal.
public static class ExtraShrines
{
    public const int MaxCount = 32;
    public const float ChargeZoneReach = 12.5f;
    // An authored spot's height is only approximate, so its floor is looked for this far above it and below it.
    // Authored spots closer than this to a shrine already placed are not used, so no two shrines stack on one spot.
    public const float MinSpotGap = ChargeZoneReach;
    // Each authored Charge Shrine is golden (legendary offers) with this chance, drawn again every run. The game's own chance is 0.008, so golden shrines stay uncommon.
    public const float GoldenChance = 0.1f;
    public const float SpotFloorAbove = 3f;
    public const float SpotFloorBelow = 8f;
    // An authored spot is an anchor: when a shrine does not fit exactly there, the nearest spot that fits within this many rings is used.
    public const float NudgeStep = 2f;
    public const int NudgeRings = 4;
    public const int NudgeDirections = 8;

    private static readonly Dictionary<string, ExtraShrineKind> ComponentKinds = new()
    {
        ["InteractableShrineChallenge"] = ExtraShrineKind.Challenge,
        ["InteractableShrineMagnet"] = ExtraShrineKind.Magnet,
        ["InteractableShrineCursed"] = ExtraShrineKind.Cursed,
        ["InteractableShrineGreed"] = ExtraShrineKind.Greed,
        ["InteractableShrineBalance"] = ExtraShrineKind.Balance,
        ["InteractableShrineMoai"] = ExtraShrineKind.Moai,
        ["ChargeShrine"] = ExtraShrineKind.Charge,
    };

    public static bool Enabled(LevelFile level) => level.ExtraShrines > 0 || level.ExtraShrinesMax > 0 || level.GuaranteedShrineKinds is { Count: > 0 };

    // A uniform count in [min, max] each run, or exactly min without a maximum.
    public static int ShrineCount(int min, int? max, Random random) => max is { } high ? random.Next(min, high + 1) : min;

    // The index of the next authored spot to try, drawn with odds proportional to the square of its distance from the nearest shrine already placed, so layouts are usually spread out but two can still end up close; -1 when none is far enough.
    public static int PickSpread(IReadOnlyList<Vector3Data> spots, IReadOnlyList<Vector3Data> taken, Random random)
    {
        var weights = spots.Select(spot =>
        {
            if (taken.Count == 0) return 1f;
            var nearest = taken.Min(other => Distance(spot, other));
            return nearest < MinSpotGap ? 0f : nearest * nearest;
        }).ToList();
        var total = weights.Sum();
        if (total <= 0f) return -1;
        var target = random.NextDouble() * total;
        for (var i = 0; i < weights.Count; i++)
        {
            target -= weights[i];
            if (target < 0) return i;
        }

        return weights.FindLastIndex(weight => weight > 0f);
    }

    // Horizontal offsets to try around an authored spot, the spot itself first and then rings of directions each a step wider.
    public static List<(float X, float Z)> NudgeOffsets(float step, int rings, int directions)
    {
        var offsets = new List<(float X, float Z)> { (0f, 0f) };
        for (var ring = 1; ring <= rings; ring++)
        for (var i = 0; i < directions; i++)
        {
            var angle = i * 2f * MathF.PI / directions;
            offsets.Add((MathF.Cos(angle) * ring * step, MathF.Sin(angle) * ring * step));
        }

        return offsets;
    }

    // The kinds named in order, one per name; a name repeated is a repeated kind.
    public static List<ExtraShrineKind> ParseKinds(IReadOnlyList<string> names) =>
        (names ?? Array.Empty<string>()).Select(name => Enum.TryParse<ExtraShrineKind>(name, true, out var kind)
            ? kind
            : throw new ArgumentException($"Unknown shrine kind '{name}'.")).ToList();

    // The items in a random order, leaving the input as it was.
    public static List<T> Shuffled<T>(IReadOnlyList<T> items, Random random)
    {
        var shuffled = items.ToList();
        for (var i = shuffled.Count - 1; i > 0; i--)
        {
            var j = random.Next(i + 1);
            (shuffled[i], shuffled[j]) = (shuffled[j], shuffled[i]);
        }

        return shuffled;
    }

    public static bool RollGolden(Random random, float chance) => random.NextDouble() < chance;

    public static (float Top, float Bottom) SpotFloorWindow(float authoredHeight) =>
        (authoredHeight + SpotFloorAbove, authoredHeight - SpotFloorBelow);

    public static ExtraShrineKind? KindOf(string componentName) =>
        ComponentKinds.TryGetValue(componentName, out var kind) ? kind : null;

    public static bool IsKnownKind(string name) => Enum.TryParse<ExtraShrineKind>(name, true, out _);

    // null means the full pool.
    public static IReadOnlySet<ExtraShrineKind> AllowedKinds(IReadOnlyList<string> names)
    {
        if (names == null || names.Count == 0) return null;
        var allowed = new HashSet<ExtraShrineKind>();
        foreach (var name in names)
        {
            if (!Enum.TryParse<ExtraShrineKind>(name, true, out var kind))
            {
                throw new ArgumentException($"Unknown shrine kind '{name}'.");
            }

            allowed.Add(kind);
        }

        return allowed;
    }

    public static bool HotPathClear(Vector3Data point, IReadOnlyList<Vector3Data> anchors,
        IReadOnlyList<(Vector3Data From, Vector3Data To)> routes, float clear) =>
        anchors.All(anchor => Distance(point, anchor) >= clear)
        && routes.All(route => SegmentDistance(point, route.From, route.To) >= clear);

    public static bool ShrineClear(Vector3Data point, IReadOnlyList<Vector3Data> shrinePositions, float keepClear) =>
        shrinePositions.All(position => Distance(point, position) >= keepClear);

    public static float Distance(Vector3Data a, Vector3Data b)
    {
        var dx = a.X - b.X;
        var dy = a.Y - b.Y;
        var dz = a.Z - b.Z;
        return MathF.Sqrt(dx * dx + dy * dy + dz * dz);
    }

    public static float SegmentDistance(Vector3Data point, Vector3Data from, Vector3Data to)
    {
        var dx = to.X - from.X;
        var dy = to.Y - from.Y;
        var dz = to.Z - from.Z;
        var lengthSquared = dx * dx + dy * dy + dz * dz;
        if (lengthSquared <= float.Epsilon) return Distance(point, from);
        var t = Math.Clamp(((point.X - from.X) * dx + (point.Y - from.Y) * dy + (point.Z - from.Z) * dz) / lengthSquared, 0f, 1f);
        return Distance(point, new Vector3Data(from.X + t * dx, from.Y + t * dy, from.Z + t * dz));
    }
}
