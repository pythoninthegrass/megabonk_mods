using System;
using System.IO;
using System.Text;

namespace MegabonkLevels;

// Which steam_api64 the game actually loaded. A readiness answer only means something next to that, because the
// development stub answers Steamworks calls with no Steam behind them.
public static class SteamLibraryReport
{
    public const string StubMarker = "MEGABONK_STEAM_FAIL_INIT";

    public static string Classify(byte[] dllBytes)
    {
        if (dllBytes == null)
        {
            return "missing";
        }

        return Contains(dllBytes, Encoding.ASCII.GetBytes(StubMarker)) ? "stub" : "original";
    }

    public static string FromGameRoot(string gameRootPath)
    {
        try
        {
            var path = Path.Combine(gameRootPath, "Megabonk_Data", "Plugins", "x86_64", "steam_api64.dll");
            return Classify(File.Exists(path) ? File.ReadAllBytes(path) : null);
        }
        catch (Exception)
        {
            return "unknown";
        }
    }

    private static bool Contains(byte[] haystack, byte[] needle)
    {
        for (var i = 0; i <= haystack.Length - needle.Length; i++)
        {
            var found = true;
            for (var j = 0; j < needle.Length; j++)
            {
                if (haystack[i + j] != needle[j])
                {
                    found = false;
                    break;
                }
            }

            if (found)
            {
                return true;
            }
        }

        return false;
    }
}
