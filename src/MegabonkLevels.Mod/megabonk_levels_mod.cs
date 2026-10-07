using MelonLoader;
using UnityEngine;

[assembly: MelonInfo(typeof(MegabonkLevels.MegabonkLevelsMod), "MegabonkLevels", "0.0.1", "pythoninthegrass")]
[assembly: MelonGame("", "Megabonk")]

namespace MegabonkLevels;

public class MegabonkLevelsMod : MelonMod
{
    public override void OnInitializeMelon()
    {
        LoggerInstance.Msg("MegabonkLevels mod initialized.");
        GenerationPatch.Install(LoggerInstance);
        SeedForcePatch.Install(LoggerInstance);
        GridShapePatch.Install(LoggerInstance);
        NavMeshPatch.Install(LoggerInstance);
    }

    public override void OnUpdate()
    {
        if (Input.GetKeyDown(KeyCode.F9))
        {
            SeedForcePatch.CycleMode();
        }
    }
}
