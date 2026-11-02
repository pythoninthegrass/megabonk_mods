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

    public static bool Enabled(LevelFile level) => level.ExtraShrines > 0;

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
