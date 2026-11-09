using System.Collections.Generic;

namespace MegabonkLevels;

// One CharacterData.statModifiers row, reduced to what a stat total needs.
public readonly record struct StatModifierRow(int Stat, byte ModifyType, float Modification);

// Decides when a run borrows another character's landing stats, and what that character's own total for a stat is.
public static class FallDamagePolicy
{
    public const int FallDamageReductionStat = 27;
    public const int MaxHealthStat = 0;
    public const int MoveSpeedStat = 25;

    public const byte Addition = 0;
    public const byte Multiplication = 1;
    public const byte Flat = 2;

    // The level file names the character to borrow from by the same names the harness accepts, or nothing at all.
    public static int? ReferenceCharacter(string name) => CharacterOverride.TryParseName(name);

    // A run the mod did not load keeps stock fall damage everywhere, and the reference character's own landings run
    // untouched so they stay stock in every level.
    public static bool Applies(bool customLevelActive, int? referenceCharacterId, int activeCharacterId) =>
        customLevelActive && referenceCharacterId.HasValue && referenceCharacterId.Value != activeCharacterId;

    public static bool FreeDropApplies(bool customLevelActive, float? freeHeight, float? drop) =>
        customLevelActive && freeHeight is { } height && float.IsFinite(height) && height >= 0
        && drop is { } distance && float.IsFinite(distance) && distance <= height + 0.25f;

    // Additive rows (Addition and Flat) sum onto the base, multiplicative rows scale that sum, which is how the game's
    // stat components combine them. Confirmed against the live GetStat of both Warehouse characters.
    public static float StatTotal(float baseValue, IEnumerable<StatModifierRow> rows, int stat)
    {
        var additive = baseValue;
        var multiplier = 1f;
        if (rows != null)
        {
            foreach (var row in rows)
            {
                if (row.Stat != stat)
                {
                    continue;
                }

                switch (row.ModifyType)
                {
                    case Addition:
                    case Flat:
                        additive += row.Modification;
                        break;
                    case Multiplication:
                        multiplier *= 1f + row.Modification;
                        break;
                }
            }
        }

        return additive * multiplier;
    }
}

public sealed class LandingHeightTracker
{
    private float? _groundedY;
    public float? GroundedHeight => _groundedY;

    public void ObserveContact(bool grounded, float bodyY, float? surfaceY, float bodyOffset)
    {
        if (!grounded || surfaceY is not { } floor || !float.IsFinite(bodyY) || !float.IsFinite(floor)) return;
        var clearance = bodyY - floor;
        if (clearance < -0.25f || clearance > bodyOffset + 0.5f) return;
        Observe(true, floor);
    }

    public void Observe(bool grounded, float bodyY)
    {
        if (grounded && float.IsFinite(bodyY)) _groundedY = bodyY;
    }

    public float? DropTo(float bodyY) => _groundedY is { } from && float.IsFinite(bodyY) ? from - bodyY : null;

    public void Reset() => _groundedY = null;
}
