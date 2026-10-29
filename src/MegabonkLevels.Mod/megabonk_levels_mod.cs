using System.IO;
using MelonLoader;
using MelonLoader.Utils;
using UnityEngine;

[assembly: MelonInfo(typeof(MegabonkLevels.MegabonkLevelsMod), "MegabonkLevels", "0.0.1", "pythoninthegrass")]
[assembly: MelonGame("", "Megabonk")]

namespace MegabonkLevels;

public class MegabonkLevelsMod : MelonMod
{
    // Hardcoded test level file, manually placed in the Mods folder alongside the mod DLL — see
    // docs/level-format.md for the sample and how to deploy it. Loading an arbitrary, user-chosen path
    // is not implemented.
    private const string TestLevelFileName = "megabonklevels-test-level.mblevel.json";

    public override void OnInitializeMelon()
    {
        LoggerInstance.Msg("MegabonkLevels mod initialized.");
        GenerationPatch.Install(LoggerInstance);
        SeedForcePatch.Install(LoggerInstance);
        GridShapePatch.Install(LoggerInstance);
        NavMeshPatch.Install(LoggerInstance);
        LiveEditPatch.Install(LoggerInstance);
        RailHandoffPatch.Install(LoggerInstance);
        PackPrefabs.Initialize(LoggerInstance);
        SceneTransitionProbe.Install(LoggerInstance);
        CustomLevelStatePatch.Install(LoggerInstance);
        DeathRestartPatch.Install(LoggerInstance);
        CharacterScreenPatch.Install(LoggerInstance);
        SteamWriteGuard.Install(LoggerInstance);
        DevHarness.Install(LoggerInstance);
    }

    public override void OnLateUpdate()
    {
        CameraOverride.Apply();
    }

    public override void OnUpdate()
    {
        EditorInput.Queue.BeginFrame(Time.frameCount, Time.unscaledTime, (Input.mousePosition.x, Input.mousePosition.y));
        DevHarness.Poll();
        LevelLoaderPatch.Pump();
        LiveEditPatch.TickPlayerStart(LoggerInstance);
        LiveEditPatch.TickMaxSlopeAngle(LoggerInstance);
        KillFloorWatcher.Tick();
        LevelMusic.Tick();
        PositionLabel.Tick();
        EditorMode.Tick(LoggerInstance);

        if (DevHarness.Enabled && EditorMode.Active)
        {
            EditorInput.LogRealTextInput(LoggerInstance, EditorTileTools.TextInputFocused);
        }

        if (EditorInput.GetKeyDown(KeyCode.F9))
        {
            SeedForcePatch.CycleMode();
        }

        // F6, not F10: F10 is already bound to the game's own built-in debug console.
        if (EditorInput.GetKeyDown(KeyCode.F6))
        {
            var path = Path.Combine(MelonEnvironment.ModsDirectory, TestLevelFileName);
            LevelLoaderPatch.LoadAndStart(path, LoggerInstance);
        }
    }
}
