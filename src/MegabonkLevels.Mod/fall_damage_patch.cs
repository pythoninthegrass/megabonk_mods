using System.Collections.Generic;
using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppAssets.Scripts.Inventory__Items__Pickups;
using Il2CppAssets.Scripts.Inventory__Items__Pickups.Stats;
using Il2CppAssets.Scripts.Menu.Shop;
using HarmonyLib;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// A level that names a reference character scores landings with that character's fall damage reduction. The stat is
// the whole per-character difference in the game's own numbers (both Warehouse characters share one PlayerHealth, so
// the 30/140 m/s thresholds are the same), so the patch swaps it into the player's stat dictionaries for the duration
// of PlayerHealth.OnPlayerLanded and puts the player's own value back in the postfix. See FallDamagePolicy for when it
// applies and docs/development.md for the measured curve.
public static class FallDamagePatch
{
    private const EStat Stat = EStat.FallDamageReduction;

    private static MelonLogger.Instance _logger;
    private static int _swapCount;
    private static float _lastPlayerValue = float.NaN;
    private static float _lastReferenceValue = float.NaN;
    private static float _lastReadBack = float.NaN;

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    // The character whose landing stats this level borrows, from the level file, or null when it names none.
    public static int? ReferenceCharacterId => FallDamagePolicy.ReferenceCharacter(LiveEditPatch.FallDamageCharacter);

    public static bool IsActive => FallDamagePolicy.Applies(CustomLevelState.IsActive, ReferenceCharacterId, ActiveCharacterId);

    public static int ActiveCharacterId => (int)(MyPlayer.Instance ? MyPlayer.Instance.character : (ECharacter)(-1));

    public static int SwapCount => _swapCount;

    public static float LastPlayerValue => _lastPlayerValue;

    public static float LastReferenceValue => _lastReferenceValue;

    // What GetStat reports with the swap in place: the reference character's total, unless the game reads the stat
    // somewhere the patch does not reach.
    public static float LastReadBack => _lastReadBack;

    // The reference character's own total for the stat, read from its CharacterData so the numbers come from the game.
    public static float ReferenceValue()
    {
        if (ReferenceCharacterId is not { } id)
        {
            return float.NaN;
        }

        var data = DataManager.Instance ? DataManager.Instance.GetCharacterData((ECharacter)id) : null;
        if (data == null)
        {
            return float.NaN;
        }

        return FallDamagePolicy.StatTotal(PlayerStatsNew.GetBaseValue(Stat), Rows(data), FallDamagePolicy.FallDamageReductionStat);
    }

    private static IEnumerable<StatModifierRow> Rows(CharacterData data)
    {
        foreach (var modifier in data.statModifiers ?? new Il2CppSystem.Collections.Generic.List<StatModifier>())
        {
            yield return new StatModifierRow((int)modifier.stat, (byte)(int)modifier.modifyType, modifier.modification);
        }
    }

    private sealed class Swapped
    {
        public Il2CppSystem.Collections.Generic.Dictionary<EStat, float> Stats;
        public Il2CppSystem.Collections.Generic.Dictionary<EStat, float> RawStats;
        public float OldStat;
        public float OldRawStat;
        public bool HadRawStat;
    }

    [HarmonyPatch(typeof(PlayerHealth), nameof(PlayerHealth.OnPlayerLanded))]
    private static class OnPlayerLandedPatch
    {
        private static bool Prefix(PlayerHealth __instance, out object __state)
        {
            __state = null;
            if (!IsActive)
            {
                return true;
            }

            var stats = MyPlayer.Instance ? MyPlayer.Instance.inventory?.playerStats : null;
            var reference = ReferenceValue();
            if (stats == null || stats.stats == null || float.IsNaN(reference))
            {
                return true;
            }

            if (!stats.stats.TryGetValue(Stat, out var old))
            {
                LogOnce($"FallDamagePatch: no {Stat} entry to swap (reference {reference:0.###}), leaving the landing stock");
                return true;
            }

            var swap = new Swapped { Stats = stats.stats, OldStat = old };
            if (stats.rawStats != null && stats.rawStats.TryGetValue(Stat, out var oldRaw))
            {
                swap.RawStats = stats.rawStats;
                swap.OldRawStat = oldRaw;
                swap.HadRawStat = true;
            }

            stats.stats[Stat] = reference;
            if (swap.HadRawStat)
            {
                swap.RawStats[Stat] = reference;
            }
            __state = swap;
            _swapCount++;
            _lastPlayerValue = old;
            _lastReferenceValue = reference;
            _lastReadBack = stats.GetStat(Stat);
            LogOnce($"FallDamagePatch: landing at hp {__instance.hp:0} scored with {Stat} {old:0.###} -> {reference:0.###} (GetStat {_lastReadBack:0.###})");
            return true;
        }

        private static void Postfix(object __state)
        {
            if (__state is not Swapped swap)
            {
                return;
            }

            swap.Stats[Stat] = swap.OldStat;
            if (swap.HadRawStat)
            {
                swap.RawStats[Stat] = swap.OldRawStat;
            }
        }
    }

    // Landings repeat the swap on every drop, so the first few are the evidence and the rest stay quiet; the harness
    // fall-damage readout carries the latest values whenever they are needed.
    private static void LogOnce(string message)
    {
        if (_swapCount <= 3)
        {
            _logger?.Msg(message);
        }
    }
}
