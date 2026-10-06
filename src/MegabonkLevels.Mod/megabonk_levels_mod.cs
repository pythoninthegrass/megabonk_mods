using MelonLoader;

[assembly: MelonInfo(typeof(MegabonkLevels.MegabonkLevelsMod), "MegabonkLevels", "0.0.1", "pythoninthegrass")]
[assembly: MelonGame("", "Megabonk")]

namespace MegabonkLevels;

public class MegabonkLevelsMod : MelonMod
{
    public override void OnInitializeMelon()
    {
        LoggerInstance.Msg("MegabonkLevels mod initialized.");
    }
}
