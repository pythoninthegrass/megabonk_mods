using System;
using System.Linq;
using Assets.Scripts.MapGeneration.ProceduralTiles;
using Il2CppInterop.Runtime.InteropTypes.Arrays;
using UnityEngine;

namespace MegabonkLevels;

// Logs ProceduralTileGeneration.proceduralTiles' actual runtime shape and the StageData.mapParameters
// values that are supposed to drive tile spacing, then cross-checks that spacing against the measured
// world distance between two adjacent occupied grid cells (TASK-002.03 AC#1/#2). currentStage/
// currentMapParameters are declared `private` in the Il2CppDumper declarations, but Il2CppInterop
// generates them as public properties backed by native field-offset reads, so they're directly
// accessible - no reflection needed.
public static class GridShapePatch
{
    public static void Install(ModLogger logger)
    {
        MapGenerationController.A_GenerationComplete += (Il2CppSystem.Action)(() => OnGenerationComplete(logger));
    }

    private static void OnGenerationComplete(ModLogger logger)
    {
        var controller = UnityEngine.Object.FindObjectOfType<MapGenerationController>();
        var tileGen = controller?.proceduralTileGeneration;
        if (tileGen == null)
        {
            logger.Msg("GridShape: no ProceduralTileGeneration instance found");
            return;
        }

        LogGridShape(logger, tileGen);
        LogSpacing(logger, tileGen);
    }

    private static void LogGridShape(ModLogger logger, ProceduralTileGeneration tileGen)
    {
        Il2CppReferenceArray<Il2CppReferenceArray<ProceduralTile>> grid = tileGen.proceduralTiles;
        if (grid == null)
        {
            logger.Msg("GridShape: proceduralTiles is null");
            return;
        }

        var rowLengths = Enumerable.Range(0, grid.Length).Select(i => grid[i]?.Length ?? -1).ToArray();
        var occupied = 0;
        for (var x = 0; x < grid.Length; x++)
        {
            var row = grid[x];
            if (row == null)
            {
                continue;
            }

            for (var y = 0; y < row.Length; y++)
            {
                if (row[y] != null)
                {
                    occupied++;
                }
            }
        }

        logger.Msg($"GridShape: proceduralTiles.Length={grid.Length} rowLengths=[{string.Join(",", rowLengths.Distinct())}] occupiedCells={occupied}");
    }

    private static void LogSpacing(ModLogger logger, ProceduralTileGeneration tileGen)
    {
        var mapParameters = tileGen.currentMapParameters ?? tileGen.currentStage?.mapParameters;

        if (mapParameters == null)
        {
            logger.Msg("GridShape: could not resolve MapParameters");
            return;
        }

        logger.Msg($"GridShape: MapParameters size={mapParameters.size} scale={mapParameters.scale} "
            + $"tileWidth={mapParameters.tileWidth} tileHeight={mapParameters.tileHeight} "
            + $"scaledTileWidth={mapParameters.scaledTileWidth} scaledTileHeight={mapParameters.scaledTileHeight}");

        var measured = MeasureAdjacentSpacing(tileGen.proceduralTiles);
        if (measured == null)
        {
            logger.Msg("GridShape: could not find two adjacent occupied cells to measure");
            return;
        }

        logger.Msg($"GridShape: measured adjacent-tile distance x={measured.Value.x:F4} z={measured.Value.z:F4}");
    }

    private static (float x, float z)? MeasureAdjacentSpacing(Il2CppReferenceArray<Il2CppReferenceArray<ProceduralTile>> grid)
    {
        if (grid == null)
        {
            return null;
        }

        for (var x = 0; x < grid.Length - 1; x++)
        {
            var row = grid[x];
            var nextRow = grid[x + 1];
            if (row == null || nextRow == null)
            {
                continue;
            }

            for (var y = 0; y < Math.Min(row.Length, nextRow.Length); y++)
            {
                var a = row[y];
                var b = nextRow[y];
                if (a == null || b == null)
                {
                    continue;
                }

                var pa = a.transform.position;
                var pb = b.transform.position;
                return (Math.Abs(pb.x - pa.x), Math.Abs(pb.z - pa.z));
            }
        }

        return null;
    }
}
