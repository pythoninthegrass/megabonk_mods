using HarmonyLib;
using Il2Cpp;
using Il2CppAssets.Scripts.Managers;
using MelonLoader;

namespace MegabonkLevels;

// Shows the death screen's own retry button for custom runs and keeps the level's edits across the game's native restart; see docs/development.md.
public static class DeathRestartPatch
{
    private static MelonLogger.Instance _logger;

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    [HarmonyPatch(typeof(DeathScreen), nameof(DeathScreen.StartDeathScreen))]
    private static class StartDeathScreenPostfix
    {
        private static void Postfix(DeathScreen __instance)
        {
            if (!CustomLevelState.IsActive || __instance.restartBtn == null)
            {
                return;
            }

            __instance.restartBtn.SetActive(true);
            _logger?.Msg("DeathRestart: retry button shown for the custom run");
        }
    }

    [HarmonyPatch(typeof(MapController), nameof(MapController.RestartRun))]
    private static class RestartRunPrefix
    {
        private static void Prefix()
        {
            if (!CustomLevelState.IsActive)
            {
                return;
            }

            LiveEditPatch.RearmLevelEdits();
            _logger?.Msg("DeathRestart: restarting the custom run, level edits queued again");
        }
    }
}
