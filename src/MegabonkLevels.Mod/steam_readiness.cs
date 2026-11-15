using System;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

// Whether the game's Steamworks client is up, read through the build id; the not-initialized fault is an expected answer while the game starts or with no Steam session.
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

        var reason = isSteamRunning != null && isSteamRunning() == false ? ReasonSteamNotRunning : ReasonClientNotInitialized;
        return new SteamReadiness(false, null, reason);
    }

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
