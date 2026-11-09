using BepInEx;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;

namespace BepInExBootSpike;

[BepInPlugin(PluginGuid, PluginName, PluginVersion)]
public class SpikePlugin : BasePlugin
{
    public const string PluginGuid = "megabonklevels.bepinex-boot-spike";
    public const string PluginName = "BepInEx Boot Spike";
    public const string PluginVersion = "0.1.0";

    internal static ManualLogSource LogSource;

    public override void Load()
    {
        LogSource = Log;
        Log.LogInfo("Spike: Load() entered");
        Harmony.CreateAndPatchAll(typeof(MainMenuAwakePatch), PluginGuid);
        AddComponent<SpikeTick>();
        Log.LogInfo("Spike: Load() complete - patch applied, tick component added");
    }
}
