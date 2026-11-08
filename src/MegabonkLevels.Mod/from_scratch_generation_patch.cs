using System;
using System.Linq;
using HarmonyLib;
using Il2Cpp;
using Il2CppAssets.Scripts.MapGeneration.ProceduralTiles;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Replaces the game's map generation with the authored grid of a from-scratch level and skips every generated object
// phase. The load path is described in docs/runtime-map-structure.md ("Replacing generation for from-scratch levels").
public static class FromScratchGenerationPatch
{
    private static MelonLogger.Instance _logger;
    private static LevelFile? _level;

    public static void Install(MelonLogger.Instance logger) => _logger = logger;

    // Set by LevelLoaderPatch for every custom load so a generated-baseline load clears an earlier from-scratch level.
    public static void Arm(LevelFile level) => _level = level.IsFromScratch ? level : null;

    public static LevelFile? ActiveLevel => _level;

    // Stays set across a death-screen restart, which regenerates the same level; CustomLevelState ends it with the run.
    private static bool Building => _level != null && CustomLevelState.IsActive;

    [HarmonyPatch(typeof(ProceduralTileGeneration), nameof(ProceduralTileGeneration.GetWorldSize))]
    private static class WorldSizePostfix
    {
        private static void Postfix(ProceduralTileGeneration __instance, ref Vector3 __result)
        {
            if (!Building) return;
            var size = FromScratchLayout.WorldSize(_level.Value.Grid.Value, __instance.currentMapParameters.scaledTileWidth,
                new Vector3Data(__result.x, __result.y, __result.z));
            __result = new Vector3(size.X, size.Y, size.Z);
        }
    }

    [HarmonyPatch(typeof(ProceduralTileGeneration), nameof(ProceduralTileGeneration.GetWorldCenter))]
    private static class WorldCenterPostfix
    {
        private static void Postfix(ProceduralTileGeneration __instance, ref Vector3 __result)
        {
            if (!Building) return;
            var origin = __instance.TilePositionToWorldPosition(Vector2Int.zero);
            var center = FromScratchLayout.WorldCenter(_level.Value.Grid.Value, __instance.currentMapParameters.scaledTileWidth,
                new Vector3Data(origin.x, origin.y, origin.z), new Vector3Data(__result.x, __result.y, __result.z));
            __result = new Vector3(center.X, center.Y, center.Z);
        }
    }

    [HarmonyPatch(typeof(ProceduralTileGeneration), nameof(ProceduralTileGeneration.Generate))]
    private static class GeneratePrefix
    {
        private static bool Prefix(ProceduralTileGeneration __instance, out Vector3 firstTileDirection, StageData stageData, MapParameters mapParameters, ref Vector3 __result)
        {
            firstTileDirection = Vector3.forward;
            if (!Building)
            {
                return true;
            }

            try
            {
                __result = Build(__instance, stageData, mapParameters, _level.Value, out firstTileDirection);
            }
            catch (Exception ex)
            {
                _logger?.Error($"FromScratch: building the authored grid threw: {ex}");
                StartupCover.OnStartFailed("from-scratch generation threw");
                throw;
            }

            return false;
        }
    }

    private static Vector3 Build(ProceduralTileGeneration tileGen, StageData stage, MapParameters stock, LevelFile level, out Vector3 firstTileDirection)
    {
        var grid = level.Grid.Value;
        var size = FromScratchLayout.GeneratorSize(grid);
        var parameters = UnityEngine.Object.Instantiate(stock);
        parameters.size = size;

        tileGen.currentStage = stage;
        tileGen.currentMapParameters = parameters;
        tileGen.debugSeed = level.Seed;
        DestroyOld(tileGen);
        tileGen.tiles = new Il2CppSystem.Collections.Generic.List<GameObject>();
        tileGen.flatTiles = new Il2CppSystem.Collections.Generic.List<GameObject>();
        tileGen.fillTiles = new Il2CppSystem.Collections.Generic.List<GameObject>();

        var columns = new Il2CppReferenceArray<Il2CppReferenceArray<ProceduralTile>>(size);
        for (var x = 0; x < size; x++)
        {
            columns[x] = new Il2CppReferenceArray<ProceduralTile>(size);
        }

        tileGen.proceduralTiles = columns;
        foreach (var cell in grid.Cells)
        {
            var tile = FromScratchLayout.TileArguments(cell);
            var direction = new Vector3(tile.DirectionX, 0, tile.DirectionZ);
            var prefab = tile.IsSlope ? tileGen.slopeTile : tileGen.flatTile;
            var created = tileGen.InstantiateTile(new Vector2Int(tile.X, tile.Z), tile.Height, prefab, direction, direction);
            columns[tile.X][tile.Z] = created.GetComponent<ProceduralTile>();
            GroundSkin.Apply(created, tile.X, tile.Z, level.GroundZones, _logger);
        }

        FillRegeneration.Regenerate(tileGen, parameters.scaledTileWidth, grid.Cells.Select(cell => (cell.X, cell.Z)), _logger, includeExterior: true);

        var parent = new GameObject("TilesParent");
        tileGen.tilesParent = parent;
        foreach (var list in new[] { tileGen.tiles, tileGen.flatTiles, tileGen.fillTiles })
        {
            for (var i = 0; i < list.Count; i++)
            {
                list[i].transform.SetParent(parent.transform, true);
            }
        }

        CollisionRebuild.Replace(tileGen, _logger);
        if (tileGen.collider == null)
        {
            throw new InvalidOperationException("the authored grid produced no collision mesh");
        }

        var spawn = level.Spawn.Value;
        var yaw = spawn.Rotation.Count == 3 ? spawn.Rotation[1] * Mathf.Deg2Rad : 0f;
        firstTileDirection = new Vector3(Mathf.Sin(yaw), 0, Mathf.Cos(yaw));
        _logger?.Msg($"FromScratch: built {grid.Cells.Count} authored tiles in a {size}x{size} generator grid, spawn {string.Join(",", spawn.Position)}");
        return new Vector3(spawn.Position[0], spawn.Position[1] - TeleportTarget.PlayerBodyOffsetY, spawn.Position[2]);
    }

    private static void DestroyOld(ProceduralTileGeneration tileGen)
    {
        foreach (var list in new[] { tileGen.tiles, tileGen.flatTiles, tileGen.fillTiles })
        {
            for (var i = 0; list != null && i < list.Count; i++)
            {
                if (list[i] != null)
                {
                    UnityEngine.Object.Destroy(list[i]);
                }
            }
        }

        if (tileGen.tilesParent != null)
        {
            UnityEngine.Object.Destroy(tileGen.tilesParent);
        }
    }

    // The tile-object phase also creates the boss spawner, so the authored one is placed here instead.
    [HarmonyPatch(typeof(GenerateTileObjects), nameof(GenerateTileObjects.Generate))]
    private static class TileObjectsPrefix
    {
        private static bool Prefix(GenerateTileObjects __instance)
        {
            if (!Building)
            {
                return true;
            }

            var spawner = _level.Value.BossSpawner.Value;
            var position = new Vector3(spawner.Position[0], spawner.Position[1], spawner.Position[2]);
            var rotation = Quaternion.Euler(spawner.Rotation[0], spawner.Rotation[1], spawner.Rotation[2]);
            var placed = UnityEngine.Object.Instantiate(__instance.bossSpawner, position, rotation);
            if (spawner.Scale is { Count: 3 } scale)
            {
                placed.transform.localScale = new Vector3(scale[0], scale[1], scale[2]);
            }

            ChildHider.Hide(placed.gameObject, spawner.HiddenChildren, _logger);
            _logger?.Msg($"FromScratch: boss spawner placed at {position}");
            return false;
        }
    }

    [HarmonyPatch(typeof(SpawnInteractables), "SpawnRails")]
    private static class SkipRails { private static bool Prefix() => !Building; }

    [HarmonyPatch(typeof(SpawnInteractables), nameof(SpawnInteractables.SpawnChests))]
    private static class SkipChests { private static bool Prefix() => !Building; }

    [HarmonyPatch(typeof(SpawnInteractables), nameof(SpawnInteractables.SpawnShrines))]
    private static class SkipShrines { private static bool Prefix() => !Building; }

    [HarmonyPatch(typeof(SpawnInteractables), "SpawnOther")]
    private static class SkipOther { private static bool Prefix() => !Building; }

    [HarmonyPatch(typeof(RandomObjectPlacer), "RandomObjectSpawner")]
    private static class SkipRandomObjects { private static bool Prefix() => !Building; }
}
