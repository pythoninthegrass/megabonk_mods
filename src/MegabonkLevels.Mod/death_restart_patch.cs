using HarmonyLib;
using Assets.Scripts.Managers;

namespace MegabonkLevels;

// Shows the death screen's own retry button for custom runs and keeps the level's edits across the game's native restart; see docs/development.md.
public static class DeathRestartPatch
{
    private static ModLogger _logger;

    public static void Install(ModLogger logger)
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
            // The game's own restart never reaches StartNewMap, so the cover has to be armed here or the
            // baseline map's spawn portal gets the last word on where the player ends up.
            StartupCover.OnRunStarting(true);
            _logger?.Msg("DeathRestart: restarting the custom run, level edits queued again");
        }
    }
}
