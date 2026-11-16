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

    // Positive evidence of a live client session: a client that never connected reports handle 0 for both.
    // Reported as evidence rather than used to veto readiness, because only a build id has been observed from a
    // genuinely ready client.
    public static bool? HasSteamSession()
    {
        try
        {
            return Steamworks.SteamAPI.GetHSteamPipe().m_HSteamPipe != 0 && Steamworks.SteamAPI.GetHSteamUser().m_HSteamUser != 0;
        }
        catch (Exception)
        {
            return null;
        }
    }

    // 0 is what a client answers when it has no depot identity at all; report it as unknown rather than
    // stamping levels with a build id no real build has.
    private static string ReadSteamBuildId()
    {
        var buildId = Steamworks.SteamApps.GetAppBuildId();
        return buildId == 0 ? null : buildId.ToString();
    }
}
