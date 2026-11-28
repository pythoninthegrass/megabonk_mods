using System;
using BepInEx;
using BepInEx.Unity.IL2CPP;
using HarmonyLib;
using UnityEngine;

namespace MegabonkLevels;

[BepInPlugin("megabonklevels.runtime", "Megabonk Level Editor", "0.3.0")] // x-release-please-version
public class MegabonkLevelsMod : BasePlugin
{
    private static ModLogger _logger;

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
    private static readonly Action _tickConsole = ConsoleOverlay.Tick;

    public override void Load()
    {
        var logger = new ModLogger(Log);
        _logger = logger;
        ModLogger.Default = _logger;
        ModTick.Instance = AddComponent<ModTick>();
        logger.Msg("MegabonkLevels mod initialized.");
        GenerationPatch.Install(logger);
        SeedForcePatch.Install(logger);
        TerrainSeedPatch.Install(logger);
        GridShapePatch.Install(logger);
        NavMeshPatch.Install(logger);
        LiveEditPatch.Install(logger);
        RailHandoffPatch.Install(logger);
        RailWallEndPatch.Install(logger);
        GrindInput.Install(logger);
        GrindGatePatch.Install(logger);
        GrindAssistWatcher.Install(logger);
        FallDamagePatch.Install(logger);
        BossSpawnRedirectPatch.Install(logger);
        BossPoolPatch.Install(logger);
        LavaWatcher.Install(logger);
        GrassMask.Install(logger);
        BossEventPatch.Install(logger);
        FromScratchGenerationPatch.Install(logger);
        ChestLuckPatch.Install(logger);
        PackPrefabs.Initialize(logger);
        LevelMusic.Initialize(logger);
        SceneTransitionProbe.Install(logger);
        CustomLevelStatePatch.Install(logger);
        DeathRestartPatch.Install(logger);
        DeathScreenPress.Install(logger);
        CharacterScreenPatch.Install(logger);
        MapSelectionPatch.Install(logger);
        SteamWriteGuard.Install(logger);
        ConsoleOverlay.Install(logger);
        DevHarness.Install(logger);
        PerfProbes.Install(logger);
        PerfMonitor.Install(logger);
        PerfGc.Install(logger);
        Harmony.CreateAndPatchAll(typeof(MegabonkLevelsMod).Assembly, "megabonklevels.runtime");
    }

    internal static void Tick()
    {
        PerfMonitor.Tick();
        EditorInput.Queue.BeginFrame(Time.frameCount, Time.unscaledTime, (Input.mousePosition.x, Input.mousePosition.y));

        // The backquote toggle runs before every hotkey so the F6-F9 and editor keys are skipped on the frame the
        // console takes focus, and while it stays open.
        if (EditorInput.GetKeyDown(KeyCode.BackQuote))
        {
            ConsoleOverlay.Toggle(_logger);
        }

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
        // Ticked after the editor: the console keeps rendering while the editor holds the run frozen.
        PerfMonitor.Timed(PerfTick.Console, _tickConsole);
        LavaWatcher.Tick();
        FallDamagePatch.Tick();

        if (DevHarness.Enabled && EditorMode.Active)
        {
            EditorInput.LogRealTextInput(_logger, EditorTileTools.TextInputFocused);
        }

        if (ConsoleOverlay.Focused)
        {
            return;
        }

        if (EditorInput.GetKeyDown(KeyCode.F9))
        {
            SeedForcePatch.CycleMode();
        }

        // F6, not F10: F10 is already bound to the game's own built-in debug console.
        if (EditorInput.GetKeyDown(KeyCode.F6))
        {
            LevelLoaderPatch.LoadAndStart(ModPaths.TestLevel, _logger);
        }
    }
}
