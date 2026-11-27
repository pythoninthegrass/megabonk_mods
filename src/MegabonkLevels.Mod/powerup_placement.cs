using System.Collections.Generic;
using Assets.Scripts.Inventory__Items__Pickups.Pickups;
using HarmonyLib;
using UnityEngine;

namespace MegabonkLevels;

[HarmonyPatch(typeof(PickupManager), nameof(PickupManager.SpawnPickup))]
public static class PowerupPlacement
{
    private static readonly EPickup[] Kinds =
        { EPickup.Health, EPickup.Nuke, EPickup.Time, EPickup.Shield, EPickup.Rage, EPickup.Haste, EPickup.Stonks, EPickup.Magnet };
    private static readonly List<Vector3> _spots = new();
    private static readonly List<int> _remaining = new();

    public static void Reset()
    {
        _spots.Clear();
        _remaining.Clear();
    }

    public static void SpawnInitial(IReadOnlyList<IReadOnlyList<float>> spots, ModLogger logger)
    {
        Reset();
        if (spots == null || PickupManager.Instance == null) return;
        Physics.SyncTransforms();
        foreach (var point in spots)
        {
            if (PlacementProbe.HighestFloor(point[0], point[2], point[1] + 1f, point[1] - 1f, null, out var floor))
                _spots.Add(floor);
        }

        var random = LiveEditPatch.RunRandom.PowerupPlacement;
        for (var i = 0; i < 2 && i < _spots.Count; i++)
            PickupManager.Instance.SpawnPickup(Kinds[random.Next(Kinds.Length)], _spots[0], 1, false, 0f);
        logger.Msg($"PowerupPlacement: {_spots.Count}/{spots.Count} approved spots supported");
    }

    private static void Prefix(EPickup __0, ref Vector3 __1, ref bool __3)
    {
        if (!CustomLevelState.IsActive || _spots.Count == 0 || System.Array.IndexOf(Kinds, __0) < 0) return;
        if (_remaining.Count == 0)
        {
            for (var i = 0; i < _spots.Count; i++) _remaining.Add(i);
        }
        var pick = LiveEditPatch.RunRandom.PowerupPlacement.Next(_remaining.Count);
        __1 = _spots[_remaining[pick]];
        _remaining.RemoveAt(pick);
        __3 = false;
    }
}
