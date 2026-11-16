using System;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

// Whether the game's Steamworks client is up. The build id answers for it, and the reason for its absence comes
// from the shim; which steam_api64 is loaded decides how much a build id is worth.
public readonly record struct SteamReadiness(bool Ready, string BuildId, string Reason = null)
{
    public const string NotInitializedMessage = "Steamworks is not initialized";
    public const string ReasonClientNotInitialized = "client-not-initialized";
    public const string ReasonSteamNotRunning = "steam-not-running";

    public static bool IsNotInitialized(Exception error) => error != null && error.Message.Contains(NotInitializedMessage);

    public static SteamReadiness Probe(Func<string> currentBuildId, Func<bool?> isSteamRunning = null)
    {
        string buildId;
        try
        {
            buildId = currentBuildId();
        }
        catch (Exception ex) when (IsNotInitialized(ex))
        {
            buildId = null;
        }

        if (buildId != null)
        {
            return new SteamReadiness(true, buildId);
        }

        bool? running;
        try
        {
            running = isSteamRunning?.Invoke();
        }
        catch (Exception)
        {
            running = null;
        }

        return new SteamReadiness(false, null, ReasonFor(running));
    }

    private static string ReasonFor(bool? running) => running == false ? ReasonSteamNotRunning : ReasonClientNotInitialized;

    public JsonObject ToJson()
    {
        var json = new JsonObject { ["ready"] = Ready };
        if (Ready)
        {
            json["buildId"] = BuildId;
        }
        else if (Reason != null)
        {
            json["reason"] = Reason;
        }

        return json;
    }
}
