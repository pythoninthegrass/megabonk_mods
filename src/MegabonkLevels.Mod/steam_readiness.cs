using System;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

// Whether the game's Steamworks client is up, read through the build id; the not-initialized fault is an expected answer while the game starts.
public readonly record struct SteamReadiness(bool Ready, string BuildId)
{
    private const string NotInitializedMessage = "Steamworks is not initialized";

    public static SteamReadiness Probe(Func<string> currentBuildId)
    {
        try
        {
            return new SteamReadiness(true, currentBuildId());
        }
        catch (Exception ex) when (ex.Message.Contains(NotInitializedMessage))
        {
            return new SteamReadiness(false, null);
        }
    }

    public JsonObject ToJson()
    {
        var json = new JsonObject { ["ready"] = Ready };
        if (Ready)
        {
            json["buildId"] = BuildId;
        }

        return json;
    }
}
