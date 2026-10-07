namespace MegabonkLevels;

// Compares a level file's recorded gameBuildId against the running game's actual build id
// (Steamworks.SteamApps.GetAppBuildId(), see game_build_id_patch.cs) so stale level files surface
// a warning instead of silently loading a layout that may no longer match the installed build.
public static class GameBuildIdCheck
{
    public static string MismatchWarning(string recordedBuildId, string actualBuildId)
    {
        if (string.IsNullOrEmpty(recordedBuildId) || recordedBuildId == actualBuildId)
        {
            return null;
        }

        return $"Level file was saved against gameBuildId '{recordedBuildId}' but the running game is build '{actualBuildId}' — the level layout may not reproduce exactly.";
    }
}
