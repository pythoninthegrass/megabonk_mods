using System;
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
    public static void LoadAndStart(string path, MelonLogger.Instance logger)
    {
        LevelFile level;
        try
        {
            level = LevelFileSerializer.DeserializeWithMigration(File.ReadAllText(path));
        }
        catch (Exception ex)
        {
            logger.Error($"LevelLoader: failed to read '{path}': {ex.Message}");
            return;
        }

        var warning = GameBuildIdCheck.MismatchWarning(level.GameBuildId, GameBuildIdPatch.CurrentBuildId());
        if (warning != null)
        {
            logger.Warning(warning);
        }

        var mapData = FindMapData(level.Map);
        if (mapData == null)
        {
            logger.Error($"LevelLoader: no MapData found for map={level.Map}");
            return;
        }

        if (level.StageIndex < 0 || level.StageIndex >= mapData.stages.Length)
        {
            logger.Error($"LevelLoader: stageIndex {level.StageIndex} out of range for {level.Map} ({mapData.stages.Length} stages)");
            return;
        }

        SeedForcePatch.ForceLevelSeed(level.Seed);
        LiveEditPatch.SetPendingEdits(level.Edits);

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

        logger.Msg($"LevelLoader: starting '{path}' map={level.Map} stage={level.StageIndex} tier={level.Tier} seed={level.Seed}");

        try
        {
            MapController.StartNewMap(runConfig);
        }
        catch (Exception ex)
        {
            logger.Error($"LevelLoader: StartNewMap threw: {ex}");
        }
    }

    private static MapData FindMapData(EMap map)
    {
        foreach (var candidate in Resources.FindObjectsOfTypeAll<MapData>())
        {
            if ((int)candidate.eMap == (int)map)
            {
                return candidate;
            }
        }

        return null;
    }
}
