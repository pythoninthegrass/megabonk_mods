using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Player;
using HarmonyLib;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// On a level that asks for it, the slide button is what grinding means. The game's catch calls PlayerMovement.StartRail
// directly, without consulting CanStartGrind (confirmed in game: the blocked attempts name the StartRail hook), so that
// is the hook that does the work and CanStartGrind is covered for any caller that goes through it. RailHandoffPatch asks
// the same question before carrying a grind onto the next rail at a joint. The third hook is the one that makes the
// button a hold rather than a toggle: the game keeps a player on a rail by itself, so a released button has to come them
// off it, otherwise the grind runs on after the release and only lets go at the next junction.
public static class GrindGatePatch
{
    // A blocked attempt repeats every physics frame while the player overlaps a rail with the button up, and a start can
    // be re-attempted as soon as it is pressed again, so either line comes out at most this often.
    private const int LogIntervalFrames = 60;

    private static MelonLogger.Instance _logger;
    private static int _lastBlockLogFrame = -LogIntervalFrames;
    private static int _lastStartLogFrame = -LogIntervalFrames;

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    // Whether grinding is gated on this run at all.
    private static bool GateInForce => GrindGate.UsesGate(CustomLevelState.IsActive, LiveEditPatch.GrindRequiresSlide);

    // Whether the button, at this moment, allows grinding.
    private static bool SlideAllowsGrind => GrindGate.AllowsGrind(CustomLevelState.IsActive, LiveEditPatch.GrindRequiresSlide, GrindInput.IsSlideHeld());

    [HarmonyPatch(typeof(PlayerMovement), nameof(PlayerMovement.CanStartGrind))]
    private static class CanStartGrindGate
    {
        private static bool Prefix(PlayerMovement __instance, ref bool __result)
        {
            if (SlideAllowsGrind || __instance.IsGrinding())
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
            // The player on a rail already: whether they belong there is RailMovementRelease's question, not this one.
            if (__instance.IsGrinding())
            {
                return true;
            }

            if (!SlideAllowsGrind)
            {
                LogBlock("StartRail", __instance);
                return false;
            }

            if (GateInForce)
            {
                LogStart(rail, __instance);
            }

            return true;
        }
    }

    [HarmonyPatch(typeof(PlayerMovement), "RailMovement")]
    private static class RailMovementRelease
    {
        // The game's per-frame grind step, the same one RailWallEndPatch watches. Once off the rail the player stays off:
        // the catch above refuses to put them back while the button is up, and pressing it again catches the rail anew.
        private static void Postfix(PlayerMovement __instance)
        {
            if (!GateInForce || GrindInput.IsSlideHeld() || !__instance.IsGrinding())
            {
                return;
            }

            var body = __instance.rb.position;
            var progress = __instance.progress;
            __instance.StopRail();
            _logger?.Msg($"GrindGate: slide released, the grind ends at ({body.x:F1}, {body.y:F1}, {body.z:F1}), progress {progress:F3}.");
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
