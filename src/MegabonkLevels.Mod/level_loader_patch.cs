using System;
using System.Collections.Generic;
using System.IO;
using Il2Cpp;
using Il2CppAssets.Scripts.Game.Other;
using Il2CppAssets.Scripts.Managers;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// TASK-004.01: reads a .mblevel.json file (TASK-003's LevelFileSerializer) and starts a Megabonk run
// matching its map/stage/tier/seed. The seed is forced through SeedForcePatch's debugSeed hook, the
// field TASK-002.02 confirmed actually controls Tiles-map generation (see
// docs/map-generation-determinism.md) — MapGenerationController.mapSeed is a separate, disconnected
// value and must never be used to force reproduction. The run itself starts via
// MapController.StartNewMap(RunConfig) — confirmed live (SceneTransitionProbe) to be what the game's
// own normal map-select-and-confirm flow calls. TestMap(RunConfig) was the original hypothesis but
// only stages currentMap/currentStage/runConfig without leaving the main menu (confirmed live:
// MapController.IsMainMenu() stayed true before and after calling it) — it never actually starts a run.
public static class LevelLoaderPatch
{
    // Levels whose MapData isn't loaded yet wait here and are retried each frame by Pump() until the
    // main scene provides the map, so a load-level issued during startup doesn't fail with
    // "no MapData found". Each entry is removed once the run starts or the load is fatally rejected.
    private static readonly List<(LevelFile Level, MelonLogger.Instance Logger, string Path, float QueuedAt)> _pending = new();

    // Reads a .mblevel.json from disk and registers the matching run. MapData may not exist yet when
    // this is called (e.g. a load-level issued right after launch), so the load is queued and Pump()
    // attempts it each frame until the map is available. Read/parse failures return false at once.
    public static bool LoadAndStart(string path, MelonLogger.Instance logger, LoadOverrides overrides = default)
    {
        LevelFile level;
        try
        {
            level = overrides.Apply(LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(path)));
        }
        catch (Exception ex)
        {
            logger.Error($"LevelLoader: failed to read '{path}': {ex.Message}");
            return false;
        }

        foreach (var (packId, recordedVersion) in level.Packs)
        {
            var packWarning = GamePackVersionCheck.MismatchWarning(packId, recordedVersion, PackPrefabs.ManifestVersion(packId));
            if (packWarning != null)
            {
                logger.Warning(packWarning);
            }
        }

        var buildWarning = GameBuildIdCheck.MismatchWarning(level.GameBuildId, GameBuildIdPatch.CurrentBuildId());
        if (buildWarning != null)
        {
            logger.Warning(buildWarning);
        }

        _pending.Add((level, logger, path, Time.realtimeSinceStartup));
        return true;
    }

    // Attempts every pending load, dropping each once it starts or is fatally rejected. A load whose
    // MapData isn't available yet is left in place for the next Pump.
    public static void Pump()
    {
        for (var i = _pending.Count - 1; i >= 0; i--)
        {
            var (level, logger, _, queuedAt) = _pending[i];
            if (StartOnce(level, logger))
            {
                _pending.RemoveAt(i);
            }
            else if (Time.realtimeSinceStartup - queuedAt > MapDataWaitSeconds)
            {
                RejectMissingMap(level.Map, logger);
                _pending.RemoveAt(i);
            }
        }
    }

    // Starts a run from an in-memory level file, reusing the same seed forcing, pending-edit and
    // custom-run marking as a disk load. Returns false when the MapData isn't loaded yet (Pump
    // retries); returns true once the run starts or the load is fatally rejected.
    private static bool StartOnce(LevelFile level, MelonLogger.Instance logger)
    {
        var mapData = FindMapData(level.Map);
        if (mapData == null)
        {
            return false;
        }

        if (level.StageIndex < 0 || level.StageIndex >= mapData.stages.Length)
        {
            logger.Error($"LevelLoader: load failed: stageIndex {level.StageIndex} out of range for {level.Map} ({mapData.stages.Length} stages)");
            return true;
        }

        SeedForcePatch.ForceLevelSeed(level.Seed);
        LiveEditPatch.SetPendingEdits(level.Edits, level.NoGrass, level.PlayerStart, level.MaxSlopeAngle);
        CustomLevelState.MarkPendingStart();

        var runConfig = new RunConfig
        {
            mapData = mapData,
            stageData = mapData.stages[level.StageIndex],
            mapTierIndex = level.Tier,
        };

        var characterWarning = CharacterOverride.TryApply(id => CharacterMenu.selectedCharacter = (ECharacter)id);
        if (characterWarning != null)
        {
            logger.Warning(characterWarning);
        }

        logger.Msg($"LevelLoader: starting map={level.Map} stage={level.StageIndex} tier={level.Tier} seed={level.Seed}");

        try
        {
            MapController.StartNewMap(runConfig);
        }
        catch (Exception ex)
        {
            logger.Error($"LevelLoader: StartNewMap threw: {ex}");
            return true;
        }

        return true;
    }

    // How long a load waits for its MapData before it is rejected as a permanent failure.
    private const float MapDataWaitSeconds = 20f;

    private static void RejectMissingMap(EMap map, MelonLogger.Instance logger)
    {
        var available = new List<string>();
        foreach (var candidate in Resources.FindObjectsOfTypeAll<MapData>())
        {
            available.Add($"{candidate.name}={(int)candidate.eMap}");
        }

        logger.Error($"LevelLoader: load failed: no MapData found for map={map} ({(int)map}); available: {string.Join(", ", available)}");
    }

    private static MapData FindMapData(EMap map) => CatalogPrefabs.TryFindMap(map);
}
