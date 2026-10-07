using System.IO;
using MelonLoader;
using MelonLoader.Utils;
using UnityEngine;

[assembly: MelonInfo(typeof(MegabonkLevels.MegabonkLevelsMod), "MegabonkLevels", "0.0.1", "pythoninthegrass")]
[assembly: MelonGame("", "Megabonk")]

namespace MegabonkLevels;

public class MegabonkLevelsMod : MelonMod
{
    // TASK-004.01: hardcoded test level file, manually placed in the Mods folder alongside the mod
    // DLL — see docs/level-format.md for the sample and how to deploy it. Edit application (loading
    // an arbitrary, user-chosen path) is TASK-004.02's job.
    private const string TestLevelFileName = "megabonklevels-test-level.mblevel.json";

    public override void OnInitializeMelon()
    {
        LoggerInstance.Msg("MegabonkLevels mod initialized.");
        GenerationPatch.Install(LoggerInstance);
        SeedForcePatch.Install(LoggerInstance);
        GridShapePatch.Install(LoggerInstance);
        NavMeshPatch.Install(LoggerInstance);
        SceneTransitionProbe.Install(LoggerInstance);
    }

    public override void OnUpdate()
    {
        if (Input.GetKeyDown(KeyCode.F9))
        {
            SeedForcePatch.CycleMode();
        }

        // F6, not F10: F10 is already bound to the game's own built-in debug console.
        if (Input.GetKeyDown(KeyCode.F6))
        {
            var path = Path.Combine(MelonEnvironment.ModsDirectory, TestLevelFileName);
            LevelLoaderPatch.LoadAndStart(path, LoggerInstance);
        }
    }
}
