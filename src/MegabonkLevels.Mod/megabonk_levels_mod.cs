using System;
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

    private static MelonLogger.Instance _logger;

    // Cached so the per-frame perf timers cost no delegate allocations; see PerfMonitor.Timed.
    private static readonly Action _pollHarness = DevHarness.Poll;
    private static readonly Action _pumpLoad = LevelLoaderPatch.Pump;
    private static readonly Action _tickStartupCover = () => StartupCover.Tick(_logger);
    private static readonly Action _tickMaxSlopeAngle = () => LiveEditPatch.TickMaxSlopeAngle(_logger);
    private static readonly Action _tickKillFloor = KillFloorWatcher.Tick;
    private static readonly Action _tickGrindAssist = GrindAssistWatcher.Tick;
    private static readonly Action _tickLevelMusic = LevelMusic.Tick;
    private static readonly Action _tickMenuNotice = MenuNotice.Tick;
    private static readonly Action _tickPositionLabel = PositionLabel.Tick;
    private static readonly Action _tickEditorMode = () => EditorMode.Tick(_logger);

    public override void OnInitializeMelon()
    {
        _logger = LoggerInstance;
        LoggerInstance.Msg("MegabonkLevels mod initialized.");
        GenerationPatch.Install(LoggerInstance);
        SeedForcePatch.Install(LoggerInstance);
        TerrainSeedPatch.Install(LoggerInstance);
        GridShapePatch.Install(LoggerInstance);
        NavMeshPatch.Install(LoggerInstance);
        LiveEditPatch.Install(LoggerInstance);
        RailHandoffPatch.Install(LoggerInstance);
        RailWallEndPatch.Install(LoggerInstance);
        GrindInput.Install(LoggerInstance);
        GrindGatePatch.Install(LoggerInstance);
        GrindAssistWatcher.Install(LoggerInstance);
        FallDamagePatch.Install(LoggerInstance);
        BossSpawnRedirectPatch.Install(LoggerInstance);
        BossPoolPatch.Install(LoggerInstance);
        LavaWatcher.Install(LoggerInstance);
        GrassMask.Install(LoggerInstance);
        BossEventPatch.Install(LoggerInstance);
        FromScratchGenerationPatch.Install(LoggerInstance);
        ChestLuckPatch.Install(LoggerInstance);
        PackPrefabs.Initialize(LoggerInstance);
        LevelMusic.Initialize(LoggerInstance);
        SceneTransitionProbe.Install(LoggerInstance);
        CustomLevelStatePatch.Install(LoggerInstance);
        DeathRestartPatch.Install(LoggerInstance);
        DeathScreenPress.Install(LoggerInstance);
        CharacterScreenPatch.Install(LoggerInstance);
        MapSelectionPatch.Install(LoggerInstance);
        SteamWriteGuard.Install(LoggerInstance);
        DevHarness.Install(LoggerInstance);
        PerfProbes.Install(LoggerInstance);
        PerfMonitor.Install(LoggerInstance);
        PerfGc.Install(LoggerInstance);
    }

    public override void OnLateUpdate()
    {
        CameraOverride.Apply();
    }

    public override void OnDeinitializeMelon() => LevelMusic.Clear();

    public override void OnUpdate()
    {
        PerfMonitor.Tick();
        EditorInput.Queue.BeginFrame(Time.frameCount, Time.unscaledTime, (Input.mousePosition.x, Input.mousePosition.y));
        PerfMonitor.Timed(PerfTick.DevHarnessPoll, _pollHarness);
        PerfMonitor.Timed(PerfTick.LoadPump, _pumpLoad);
        PerfMonitor.Timed(PerfTick.StartupCover, _tickStartupCover);
        PerfMonitor.Timed(PerfTick.MaxSlopeAngle, _tickMaxSlopeAngle);
        PerfMonitor.Timed(PerfTick.KillFloor, _tickKillFloor);
        PerfMonitor.Timed(PerfTick.GrindAssist, _tickGrindAssist);
        PerfMonitor.Timed(PerfTick.LevelMusic, _tickLevelMusic);
        PerfMonitor.Timed(PerfTick.MenuNotice, _tickMenuNotice);
        PerfMonitor.Timed(PerfTick.PositionLabel, _tickPositionLabel);
        PerfMonitor.Timed(PerfTick.EditorMode, _tickEditorMode);
        LavaWatcher.Tick();

        if (DevHarness.Enabled && EditorMode.Active)
        {
            EditorInput.LogRealTextInput(_logger, EditorTileTools.TextInputFocused);
        }

        if (EditorInput.GetKeyDown(KeyCode.F9))
        {
            SeedForcePatch.CycleMode();
        }

        // F6, not F10: F10 is already bound to the game's own built-in debug console.
        if (EditorInput.GetKeyDown(KeyCode.F6))
        {
            var path = Path.Combine(MelonEnvironment.ModsDirectory, TestLevelFileName);
            LevelLoaderPatch.LoadAndStart(path, _logger);
        }
    }
}
