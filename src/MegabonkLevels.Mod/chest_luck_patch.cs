using System;
using System.Collections.Generic;
using HarmonyLib;
using Il2CppAssets.Scripts.Inventory__Items__Pickups.Items;
using MelonLoader;

namespace MegabonkLevels;

// Adds the run's chest luck shift to the luck the game rolls chest loot with, for levels that set chestLuckRange.
public static class ChestLuckPatch
{
    private static float _shift;
    private static MelonLogger.Instance _logger;

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    // Draws this run's shift; called once per generation, so a restart of the run draws it again.
    public static void Roll(IReadOnlyList<float> range, MelonLogger.Instance logger)
    {
        _shift = ChestLuck.Roll(range, new Random(Guid.NewGuid().GetHashCode()));
        if (range != null) logger.Msg($"ChestLuck: this run's chest luck shift is {_shift:F2} (range {range[0]:F2} to {range[1]:F2})");
    }

    [HarmonyPatch(typeof(ItemUtility), nameof(ItemUtility.GetRandomChestItem))]
    private static class GetRandomChestItemPrefix
    {
        private static void Prefix(ref float luck)
        {
            if (_shift == 0f || !CustomLevelState.IsActive) return;
            var shifted = ChestLuck.Apply(luck, _shift);
            _logger?.Msg($"ChestLuck: chest loot rolled with luck {luck:F2} shifted to {shifted:F2}");
            luck = shifted;
        }
    }
}
