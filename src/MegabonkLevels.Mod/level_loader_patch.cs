using System;
using System.Collections.Generic;
using System.IO;
using HarmonyLib;
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
    private static readonly List<(LevelFile Level, MelonLogger.Instance Logger, string Path, float QueuedAt, string Character, bool Unseeded)> _pending = new();

    // The level's allowedCharacters as loaded, kept so an editor save writes them back.
    public static IReadOnlyList<string> AllowedCharacters { get; private set; }

    // The level's mapDescription as loaded, kept so an editor save writes it back.
    public static string MapDescription { get; private set; }

    public static void ApplyMetadata(LevelFile level)
    {
        AllowedCharacters = level.AllowedCharacters;
        MapDescription = level.MapDescription;
    }

    private static bool TryRead(string path, MelonLogger.Instance logger, LoadOverrides overrides, out LevelFile level)
    {
        level = default;
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

        foreach (var (packId, revision) in level.PackKitVersions ?? new Dictionary<string, string>())
        {
            var kitWarning = GamePackVersionCheck.KitMismatchWarning(packId, revision, PackPrefabs.KitVersion(packId));
            if (kitWarning != null)
            {
                logger.Warning(kitWarning);
            }
        }

        var buildWarning = GameBuildIdCheck.MismatchWarning(level.GameBuildId, GameBuildIdPatch.CurrentBuildId());
        if (buildWarning != null)
        {
            logger.Warning(buildWarning);
        }

        return true;
    }

    // Holds the level for the very next MapController.StartNewMap, which the Map Selection Confirm calls at once; the caller has already checked the character.
    public static bool HoldForNextStart(string path, MelonLogger.Instance logger)
    {
        if (!TryRead(path, logger, default, out var level))
        {
            return false;
        }

        _awaitingCharacter = (level, logger, false, false);
        return true;
    }

    // Reads a .mblevel.json from disk and registers the matching run. MapData may not exist yet when
    // this is called (e.g. a load-level issued right after launch), so the load is queued and Pump()
    // attempts it each frame until the map is available. Read/parse failures return false at once.
    public static bool LoadAndStart(string path, MelonLogger.Instance logger, LoadOverrides overrides = default)
    {
        if (!TryRead(path, logger, overrides, out var level))
        {
            return false;
        }

        _pending.Add((level, logger, path, Time.realtimeSinceStartup, overrides.Character, overrides.Unseeded));
        return true;
    }

    // Attempts every pending load, dropping each once it starts or is fatally rejected. A load whose
    // MapData isn't available yet is left in place for the next Pump.
    public static void Pump()
    {
        for (var i = _pending.Count - 1; i >= 0; i--)
        {
            var (level, logger, _, queuedAt, character, unseeded) = _pending[i];
            if (StartOnce(level, logger, character, unseeded))
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
    private static bool StartOnce(LevelFile level, MelonLogger.Instance logger, string characterName, bool unseeded)
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

        int? character;
        try
        {
            character = DevCharacter.Resolve(EnvFlag.IsSet(DevVariable), characterName);
        }
        catch (ArgumentException ex)
        {
            logger.Error($"LevelLoader: load failed: {ex.Message}");
            return true;
        }

        if (character is not int characterId)
        {
            var allowedIds = CharacterPolicy.AllowedIds(level.AllowedCharacters);
            if (allowedIds != null)
            {
                _awaitingCharacter = (level, logger, true, unseeded);
                CharacterScreenPatch.SetRestricted(true, allowedIds);
                logger.Msg($"LevelLoader: waiting for a character to be confirmed on the character screen for map={level.Map}");
                return true;
            }
        }
        else
        {
            var characterWarning = CharacterOverride.TryApply(id => CharacterMenu.selectedCharacter = (ECharacter)id, characterId);
            if (characterWarning != null)
            {
                logger.Warning(characterWarning);
            }
            else
            {
                logger.Msg($"LevelLoader: character={(ECharacter)characterId}");
            }
        }

        if (RefuseOversizedGrid(level, mapData, logger))
        {
            return true;
        }

        var runConfig = PrepareRun(level, logger, mapData, unseeded);
        try
        {
            MapController.StartNewMap(runConfig);
        }
        catch (Exception ex)
        {
            StartupCover.OnStartFailed("MapController.StartNewMap threw");
            logger.Error($"LevelLoader: StartNewMap threw: {ex}");
        }

        return true;
    }

    // A from-scratch grid larger than the stage's stock generator size cannot be built; the refusal is logged and no run starts.
    private static bool RefuseOversizedGrid(LevelFile level, MapData mapData, MelonLogger.Instance logger)
    {
        if (level.Grid is not { } grid)
        {
            return false;
        }

        var reason = FromScratchLayout.SizeRefusal(grid, mapData.stages[level.StageIndex].mapParameters.size);
        if (reason == null)
        {
            return false;
        }

        StartupCover.OnCancelled("load refused");
        logger.Error($"LevelLoader: load refused: {reason}");
        return true;
    }

    // Seed, edits, music, title and custom-run marking for a run about to start; returns the config the run starts with.
    // An unseeded load hands seeding back to the game so the run shows what an unforced generation looks like.
    private static RunConfig PrepareRun(LevelFile level, MelonLogger.Instance logger, MapData mapData, bool unseeded)
    {
        if (unseeded)
        {
            SeedForcePatch.ReleaseLevelSeed();
        }
        else
        {
            SeedForcePatch.ForceLevelSeed(level.Seed);
        }

        FromScratchGenerationPatch.Arm(level);
        LiveEditPatch.SetPendingEdits(level.Edits, level.NoGrass, level.PlayerStart ?? level.Spawn?.Position, level.MaxSlopeAngle, level.KillFloorY, level.BossSpawnPosition, level.GrindRequiresSlide, level.PackKitVersions, fallDamageCharacter: level.FallDamageCharacter, randomizationSettings: level);
        LevelMusic.Prepare(level.Music, logger);
        LevelTitle.Prepare(level.Title, level.Description, logger);
        AllowedCharacters = level.AllowedCharacters;
        MapDescription = level.MapDescription;
        CustomLevelState.MarkPendingStart();
        InitialStage.Arm(level.StageIndex, EnvFlag.IsSet(DevVariable), EnvFlag.IsSet("MEGABONK_DEV_STAGE_OVERRIDE"));
        logger.Msg($"LevelLoader: starting map={level.Map} stage={level.StageIndex} tier={level.Tier} seed={(unseeded ? "game-rolled" : level.Seed.ToString())}");
        if (CustomTierCap.IsCapped(level.Tier))
        {
            logger.Msg($"LevelLoader: tier {level.Tier} capped to {CustomTierCap.MaxTier}");
        }

        return new RunConfig
        {
            mapData = mapData,
            stageData = mapData.stages[level.StageIndex],
            mapTierIndex = CustomTierCap.Clamp(level.Tier),
        };
    }

    // Set to MEGABONK_DEV=true to skip the character screen: a harness load then starts at once with the default or named character.
    private const string DevVariable = "MEGABONK_DEV";

    private static readonly InitialStageOverride InitialStage = new();

    [HarmonyPatch(typeof(MapController), nameof(MapController.LoadNextStage))]
    private static class InitialStagePrefix
    {
        private static void Prefix()
        {
            if (InitialStage.TakeBeforeAdvance(MapController.index) is int previousIndex)
            {
                MapController.index = previousIndex;
                MelonLogger.Msg($"LevelLoader: development initial stage override -> {previousIndex + 1}");
            }
        }
    }

    // A load held back until the player confirms a character on the restricted character screen.
    private static (LevelFile Level, MelonLogger.Instance Logger, bool RestrictsScreen, bool Unseeded)? _awaitingCharacter;

    public static bool HasAwaitingCharacter => _awaitingCharacter != null;

    public static void OnMenuDisabled(bool movingToMaps = false)
    {
        if (!MenuBackout.ShouldCancel(HasAwaitingCharacter, CharacterScreenPatch.Restricted, movingToMaps))
        {
            return;
        }

        CancelAwaitingCharacter();
        CharacterScreenPatch.SetRestricted(false);
    }

    public static void CancelAwaitingCharacter()
    {
        if (_awaitingCharacter is var (_, logger, _, _))
        {
            StartupCover.OnCancelled("load cancelled while waiting for a character");
            logger.Msg("LevelLoader: cancelled held load");
        }

        _awaitingCharacter = null;
    }

    // Swaps the confirmed run's config for the held level; the game's own flow still ends with this call.
    [HarmonyPatch(typeof(MapController), nameof(MapController.StartNewMap))]
    private static class AwaitedStartPrefix
    {
        [HarmonyPriority(Priority.First)]
        private static void Prefix(ref RunConfig newRunConfig)
        {
            if (_awaitingCharacter is not var (level, logger, restrictsScreen, unseeded) || (restrictsScreen && !CharacterScreenPatch.Restricted))
            {
                return;
            }

            var mapData = FindMapData(level.Map);
            if (mapData == null)
            {
                logger.Error($"LevelLoader: held load dropped: no MapData for map={level.Map}");
                _awaitingCharacter = null;
                return;
            }

            _awaitingCharacter = null;
            if (RefuseOversizedGrid(level, mapData, logger))
            {
                if (restrictsScreen)
                {
                    CharacterScreenPatch.SetRestricted(false);
                }

                return;
            }

            newRunConfig = PrepareRun(level, logger, mapData, unseeded);
            if (restrictsScreen)
            {
                CharacterScreenPatch.SetRestricted(false);
            }
        }
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

    public static MapData FindMapData(EMap map) => CatalogPrefabs.TryFindMap(map);
}
