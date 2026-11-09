using HarmonyLib;

namespace BepInExBootSpike;

[HarmonyPatch(typeof(MainMenu), "Awake")]
public static class MainMenuAwakePatch
{
    private static void Prefix()
    {
        SpikePlugin.LogSource.LogInfo("Spike: MainMenu.Awake prefix ran - Harmony patch is live");
    }
}
