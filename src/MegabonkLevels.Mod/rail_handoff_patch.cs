using System.Collections.Generic;
using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Player;
using HarmonyLib;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// On a custom level, a grind that runs off the end of a rail starts the nearest other rail, so rails meeting at an angle chain in both directions.
public static class RailHandoffPatch
{
    private static MelonLogger.Instance _logger;

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    [HarmonyPatch(typeof(PlayerMovement), nameof(PlayerMovement.StopRail))]
    private static class StopRailHandoff
    {
        private static void Prefix(PlayerMovement __instance, out bool __state)
        {
            var grinding = CustomLevelState.IsActive && __instance.IsGrinding();
            __state = grinding && RailHandoff.ReachedEnd(__instance.progress);
            if (grinding)
            {
                _logger?.Msg($"RailHandoff: grind stopped at progress {__instance.progress:F3}, atEnd={__state}.");
            }
        }

        private static void Postfix(PlayerMovement __instance, bool __state)
        {
            if (!__state)
            {
                return;
            }

            var body = __instance.rb.position;
            var origin = new Vector3(body.x, __instance.playerCollider.bounds.min.y, body.z);
            var colliders = Physics.OverlapSphere(origin, RailHandoff.SearchRadius, ~0, QueryTriggerInteraction.Collide);
            var rails = new List<Rail>();
            var distances = new List<float>();
            var onCooldown = new List<bool>();
            foreach (var collider in colliders)
            {
                var rail = collider.GetComponent<Rail>();
                if (rail == null)
                {
                    continue;
                }

                rails.Add(rail);
                distances.Add(Vector3.Distance(collider.ClosestPoint(origin), origin));
                onCooldown.Add(rail.IsOnCooldown());
            }

            var pick = RailHandoff.PickNearest(distances, onCooldown);
            if (pick < 0)
            {
                _logger?.Msg($"RailHandoff: no rail to move onto, {rails.Count} within {RailHandoff.SearchRadius} units.");
                return;
            }

            __instance.StartRail(rails[pick]);
            _logger?.Msg($"RailHandoff: moved onto rail at distance {distances[pick]:F2}.");
        }
    }
}
