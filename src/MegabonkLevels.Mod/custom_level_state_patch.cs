using HarmonyLib;
using Il2CppAssets.Scripts.Managers;
using MelonLoader;

namespace MegabonkLevels;

// Drives CustomLevelState.OnRunStarting() from the one method both the game's own menu flow and
// LevelLoaderPatch call to start a run (confirmed by TASK-004.01's SceneTransitionProbe), and logs the
// resulting arm/disarm so SteamWriteGuard's suppressions are auditable against a reason.
public static class CustomLevelStatePatch
{
    private static MelonLogger.Instance _logger;

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    [HarmonyPatch(typeof(MapController), nameof(MapController.StartNewMap))]
    private static class StartNewMapPrefix
    {
        private static void Prefix()
        {
            CustomLevelState.OnRunStarting();
            _logger?.Msg($"CustomLevelState: run starting, IsActive={CustomLevelState.IsActive}");
        }
    }
}
