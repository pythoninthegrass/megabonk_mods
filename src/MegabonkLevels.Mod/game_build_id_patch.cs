using System;

namespace MegabonkLevels;

// The only place the mod reads Steamworks: the running game's Steam depot build id through the game's
// bundled com.rlabrecque.steamworks.net assembly. An uninitialized client, which is normal with no
// Steam session, reads as null instead of throwing; callers treat a null build id as "unknown".
public static class GameBuildIdPatch
{
    private const string UnavailableNotice = "GameBuildId: Steamworks is not initialized; levels load and save without a game build id.";

    private static readonly BuildIdSource _source = new(ReadSteamBuildId, () => ModLogger.Default?.Warning(UnavailableNotice));

    public static string CurrentBuildId() => _source.CurrentBuildId();

    // Positive evidence only: null when the shim cannot answer, so a missing entry point is never reported as Steam being down.
    public static bool? IsSteamRunning()
    {
        try
        {
            return Steamworks.SteamAPI.IsSteamRunning();
        }
        catch (Exception)
        {
            return null;
        }
    }

    private static string ReadSteamBuildId() => Steamworks.SteamApps.GetAppBuildId().ToString();
}
