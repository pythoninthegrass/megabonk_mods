using HarmonyLib;
using Assets.Scripts.Steam;

namespace MegabonkLevels;

// Suppresses Steam leaderboard/achievement/stats writes while CustomLevelState.IsActive — a custom
// or edited level didn't come from legitimate procedural generation, and the game's
// SteamLeaderboardsManagerNew maintains a server-side banned_players board, so these calls must never
// run for a modded level. Exact targets confirmed against .tools/il2cpp_dump/dump.cs (all RVAs
// unique — safe to patch per TASK-004.01's RVA-sharing caution):
// - SteamLeaderboardsManagerNew.QueueLeaderboardUpload / .UploadLeaderboardScore (global namespace)
// - Assets.Scripts.Steam.SteamAchievementsManager.TryUnlockAchievement — the only public write entry
//   point; the unlock check and the upload queueing both happen inside it.
// - Assets.Scripts.Steam.SteamStatsManager.OnStatUpdated (private) — the bridge subscribed to
//   MyStats.A_StatUpdated that caches a stat change for Steam upload. Blocking it here leaves the
//   game's own local progression (MyStats/RunStats) untouched and only suppresses the Steam-bound copy.
public static class SteamWriteGuard
{
    private static ModLogger _logger;

    public static void Install(ModLogger logger)
    {
        _logger = logger;
    }

    private static bool ShouldRunOriginal(string callSite)
    {
        if (!CustomLevelState.IsActive)
        {
            return true;
        }

        _logger?.Msg($"SteamWriteGuard: suppressed {callSite} (custom-level run active)");
        return false;
    }

    [HarmonyPatch(typeof(SteamLeaderboardsManagerNew), nameof(SteamLeaderboardsManagerNew.QueueLeaderboardUpload))]
    private static class QueueLeaderboardUploadPrefix
    {
        private static bool Prefix() => ShouldRunOriginal(nameof(SteamLeaderboardsManagerNew.QueueLeaderboardUpload));
    }

    [HarmonyPatch(typeof(SteamLeaderboardsManagerNew), nameof(SteamLeaderboardsManagerNew.UploadLeaderboardScore))]
    private static class UploadLeaderboardScorePrefix
    {
        private static bool Prefix() => ShouldRunOriginal(nameof(SteamLeaderboardsManagerNew.UploadLeaderboardScore));
    }

    [HarmonyPatch(typeof(SteamAchievementsManager), nameof(SteamAchievementsManager.TryUnlockAchievement))]
    private static class TryUnlockAchievementPrefix
    {
        private static bool Prefix() => ShouldRunOriginal(nameof(SteamAchievementsManager.TryUnlockAchievement));
    }

    [HarmonyPatch(typeof(SteamStatsManager), "OnStatUpdated")]
    private static class OnStatUpdatedPrefix
    {
        private static bool Prefix() => ShouldRunOriginal("SteamStatsManager.OnStatUpdated");
    }
}
