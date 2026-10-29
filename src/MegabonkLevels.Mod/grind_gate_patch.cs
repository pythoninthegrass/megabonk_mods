using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Player;
using HarmonyLib;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// On a level that asks for it, a rail touch starts a grind only while the slide button is held, so riding over a coping
// rail or ollieing off a lip keeps the player's momentum. The game's catch calls StartRail directly, without consulting
// CanStartGrind (confirmed in game: the blocked attempts name the StartRail hook), so that is the hook that does the work
// and CanStartGrind is covered for any caller that goes through it. A grind already in progress is never interrupted, so
// releasing the button mid-grind keeps the player on the rail and only costs them the next one.
public static class GrindGatePatch
{
    // Blocked attempts repeat every physics frame while the player overlaps a rail, and the game calls StartRail again
    // each frame a grind runs, so either line comes out at most this often.
    private const int LogIntervalFrames = 60;

    private static MelonLogger.Instance _logger;
    private static int _lastBlockLogFrame = -LogIntervalFrames;
    private static int _lastStartLogFrame = -LogIntervalFrames;

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    // The gate is in force on a mod-loaded run of a level that asked for the slide button.
    private static bool GateInForce => GrindGate.UsesGate(CustomLevelState.IsActive, LiveEditPatch.GrindRequiresSlide);

    [HarmonyPatch(typeof(PlayerMovement), nameof(PlayerMovement.CanStartGrind))]
    private static class CanStartGrindGate
    {
        private static bool Prefix(PlayerMovement __instance, ref bool __result)
        {
            if (__instance.IsGrinding() || !GateInForce || GrindInput.IsSlideHeld())
            {
                return true;
            }

            __result = false;
            LogBlock("CanStartGrind", __instance);
            return false;
        }
    }

    [HarmonyPatch(typeof(PlayerMovement), nameof(PlayerMovement.StartRail))]
    private static class StartRailGate
    {
        private static bool Prefix(PlayerMovement __instance, Rail rail)
        {
            if (!GateInForce)
            {
                return true;
            }

            // The player on a rail already: the game calls this every frame of the grind, and a grind is never interrupted.
            if (__instance.IsGrinding())
            {
                return true;
            }

            if (!GrindInput.IsSlideHeld())
            {
                LogBlock("StartRail", __instance);
                return false;
            }

            LogStart(rail, __instance);
            return true;
        }
    }

    private static void LogBlock(string hook, PlayerMovement player)
    {
        if (Time.frameCount - _lastBlockLogFrame < LogIntervalFrames)
        {
            return;
        }

        _lastBlockLogFrame = Time.frameCount;
        var body = player.rb.position;
        _logger?.Msg($"GrindGate: slide released, grind start blocked at ({body.x:F1}, {body.y:F1}, {body.z:F1}) by the {hook} hook.");
    }

    // A placed rail's own GameObject is the collider child the catalog prefab builds, so the player's position says more
    // about which lip this is than the name does.
    private static void LogStart(Rail rail, PlayerMovement player)
    {
        if (Time.frameCount - _lastStartLogFrame < LogIntervalFrames)
        {
            return;
        }

        _lastStartLogFrame = Time.frameCount;
        var body = player.rb.position;
        var bar = rail != null ? rail.transform.position : Vector3.zero;
        _logger?.Msg($"GrindGate: slide held, grind started at ({body.x:F1}, {body.y:F1}, {body.z:F1}) on the rail at ({bar.x:F1}, {bar.y:F1}, {bar.z:F1}).");
    }
}
