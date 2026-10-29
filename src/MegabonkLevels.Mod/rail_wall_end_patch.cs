using System.Collections.Generic;
using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Player;
using HarmonyLib;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// On a custom level, a grind that would run off the end of a rail into a wall lets go of the rail with room to spare
// instead of being launched along the rail's tangent into it. Sibling of RailHandoffPatch, which covers the other case: a rail to chain onto.
public static class RailWallEndPatch
{
    private static MelonLogger.Instance _logger;

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    [HarmonyPatch(typeof(PlayerMovement), "RailMovement")]
    private static class RailMovementWallProbe
    {
        private static void Postfix(PlayerMovement __instance)
        {
            if (!CustomLevelState.IsActive || !__instance.IsGrinding())
            {
                return;
            }

            var velocity = __instance.rb.velocity;
            var travel = new Vector3(velocity.x, 0f, velocity.z);
            if (!RailWallEnd.IsMoving(travel.magnitude))
            {
                return;
            }

            var origin = __instance.rb.position;
            var rail = __instance.rail;
            var wall = NearestWall(origin, travel.normalized, __instance, rail);
            if (wall < 0f)
            {
                return;
            }

            var handoffAvailable = HandoffAvailable(origin, rail);
            if (!RailWallEnd.ShouldDetach(wall, handoffAvailable))
            {
                return;
            }

            var progress = __instance.progress;
            __instance.StopRail();
            var leaving = __instance.rb.velocity;
            var leavingSpeed = new Vector3(leaving.x, 0f, leaving.z).magnitude;
            var kept = leavingSpeed > 0.01f ? RailWallEnd.DismountSpeed(leavingSpeed) / leavingSpeed : 1f;
            leaving.x *= kept;
            leaving.z *= kept;
            leaving.y = RailWallEnd.DismountHop;
            __instance.rb.velocity = leaving;
            if (rail != null)
            {
                rail.Cooldown(__instance.playerCollider);
            }

            _logger?.Msg($"RailWallEnd: ended the grind {wall:F2} short of a wall at ({origin.x:F1}, {origin.y:F1}, {origin.z:F1}), progress {progress:F3}, speed {leavingSpeed:F1} kept {new Vector3(leaving.x, 0f, leaving.z).magnitude:F1}.");
        }

        // Distance to the nearest wall within DetachDistance ahead along the grind, or -1. The player and the rail being ground are not walls.
        private static float NearestWall(Vector3 origin, Vector3 direction, PlayerMovement player, Rail rail)
        {
            var hits = Physics.RaycastAll(origin, direction, RailWallEnd.DetachDistance, ~0, QueryTriggerInteraction.Ignore);
            var nearest = -1f;
            foreach (var hit in hits)
            {
                var collider = hit.collider;
                if (collider == null || collider.transform.root == player.transform.root)
                {
                    continue;
                }

                if (rail != null && collider.transform.root == rail.transform.root)
                {
                    continue;
                }

                if (!RailWallEnd.IsWall(hit.normal.y, Vector3.Dot(hit.normal, -direction)))
                {
                    continue;
                }

                if (nearest < 0f || hit.distance < nearest)
                {
                    nearest = hit.distance;
                }
            }

            return nearest;
        }

        // Whether a rail other than the one being ground could take the grind over, which is the case RailHandoffPatch handles.
        private static bool HandoffAvailable(Vector3 origin, Rail rail)
        {
            var colliders = Physics.OverlapSphere(origin, RailHandoff.SearchRadius, ~0, QueryTriggerInteraction.Collide);
            var distances = new List<float>();
            var onCooldown = new List<bool>();
            foreach (var collider in colliders)
            {
                var other = collider.GetComponent<Rail>();
                if (other == null || other == rail)
                {
                    continue;
                }

                distances.Add(Vector3.Distance(collider.ClosestPoint(origin), origin));
                onCooldown.Add(other.IsOnCooldown());
            }

            return RailHandoff.PickNearest(distances, onCooldown) >= 0;
        }
    }
}
