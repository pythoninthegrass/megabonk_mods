namespace MegabonkLevels;

// Wraps Steamworks.SteamApps.GetAppBuildId(), the running game's actual Steam depot build id
// (confirmed present via the game's bundled com.rlabrecque.steamworks.net assembly; SteamAPI is
// already initialized by the game itself before any mod code runs). Thin Il2Cpp-dependent wrapper
// around the pure comparison in game_build_id_check.cs.
public static class GameBuildIdPatch
{
    public static string CurrentBuildId() => Il2CppSteamworks.SteamApps.GetAppBuildId().ToString();
}
