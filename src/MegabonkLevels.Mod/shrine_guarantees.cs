using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// At least one shrine of Kind must stand inside (or, with Outside, beyond) the world-space rectangle, judged on shrines that were actually placed.
public readonly record struct ShrineGuarantee(string Kind, float MinX, float MaxX, float MinZ, float MaxZ, bool Outside = false);

public static class ShrineGuarantees
{
    public static bool Satisfies(ShrineGuarantee guarantee, ExtraShrineKind kind, Vector3Data position) =>
        ExtraShrines.ParseKinds(new[] { guarantee.Kind })[0] == kind && Inside(guarantee, position) != guarantee.Outside;

    public static IReadOnlyList<ShrineGuarantee> Unmet(IReadOnlyList<ShrineGuarantee> guarantees, IReadOnlyList<(ExtraShrineKind Kind, Vector3Data Position)> placed) =>
        (guarantees ?? Array.Empty<ShrineGuarantee>()).Where(g => !placed.Any(p => Satisfies(g, p.Kind, p.Position))).ToList();

    // The indexes of the spots that satisfy the first unmet guarantee of the kind, or null when the kind has none outstanding.
    public static IReadOnlyList<int> CandidateIndexes(IReadOnlyList<ShrineGuarantee> guarantees, ExtraShrineKind kind, IReadOnlyList<Vector3Data> spots,
        IReadOnlyList<(ExtraShrineKind Kind, Vector3Data Position)> placed)
    {
        var next = Unmet(guarantees, placed).Where(g => ExtraShrines.ParseKinds(new[] { g.Kind })[0] == kind).Cast<ShrineGuarantee?>().FirstOrDefault();
        if (next is not { } guarantee) return null;
        return Enumerable.Range(0, spots.Count).Where(i => Satisfies(guarantee, kind, spots[i])).ToList();
    }

    public static void Validate(IReadOnlyList<ShrineGuarantee> guarantees)
    {
        if (guarantees == null) return;
        foreach (var g in guarantees)
        {
            if (!ExtraShrines.IsKnownKind(g.Kind) || !float.IsFinite(g.MinX + g.MaxX + g.MinZ + g.MaxZ) || g.MinX > g.MaxX || g.MinZ > g.MaxZ)
            {
                throw new ArgumentException("Each shrine guarantee names a known kind and a world rectangle with min <= max on both axes.");
            }
        }
    }

    private static bool Inside(ShrineGuarantee g, Vector3Data p) => p.X >= g.MinX && p.X <= g.MaxX && p.Z >= g.MinZ && p.Z <= g.MaxZ;
}
