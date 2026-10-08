using System;
using System.Collections.Generic;
using System.Reflection;
using Il2Cpp;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Tile edits only move or replace the tile itself, which leaves the old wall and fill pieces around it stale and the
// sides of a new slope open to the sky. This destroys the pieces on every edge of an edited tile and asks the game's own
// per-edge builder (ProceduralTileGeneration.FillHole, private) to recreate them, so the walls match what generation
// would have built. Whole-grid FillHoles/FillEdges are not used: they would duplicate pieces everywhere.
public static class FillRegeneration
{
    private static readonly MethodInfo FillHole = typeof(ProceduralTileGeneration).GetMethod(
        "FillHole", BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public);

    public static void Regenerate(ProceduralTileGeneration tileGen, float tileWidth, IEnumerable<(int X, int Z)> touched, MelonLogger.Instance logger)
    {
        if (FillHole == null)
        {
            logger.Warning("FillRegeneration: ProceduralTileGeneration.FillHole not found; wall and fill pieces left as they were");
            return;
        }

        var grid = tileGen.proceduralTiles;
        var edges = FillEdgePlan.EdgesAround(touched, (x, z) =>
            x >= 0 && x < grid.Length && grid[x] != null && z >= 0 && z < grid[x].Length && grid[x][z] != null);

        var removed = RemoveStalePieces(tileGen, tileWidth, edges);
        var before = tileGen.fillTiles.Count;
        foreach (var edge in edges)
        {
            Build(tileGen, new Vector2Int(edge.Ax, edge.Az), new Vector2Int(edge.Bx, edge.Bz), logger);
            Build(tileGen, new Vector2Int(edge.Bx, edge.Bz), new Vector2Int(edge.Ax, edge.Az), logger);
        }

        logger.Msg($"FillRegeneration: {edges.Count} edge(s), removed {removed} stale piece(s), created {tileGen.fillTiles.Count - before}");
    }

    private static int RemoveStalePieces(ProceduralTileGeneration tileGen, float tileWidth, IReadOnlyList<CellEdge> edges)
    {
        var grid = tileGen.proceduralTiles;
        var stale = new List<GameObject>();
        for (var i = 0; i < tileGen.fillTiles.Count; i++)
        {
            var piece = tileGen.fillTiles[i];
            if (piece == null)
            {
                continue;
            }

            var position = piece.transform.position;
            foreach (var edge in edges)
            {
                var a = grid[edge.Ax][edge.Az].transform.position;
                var b = grid[edge.Bx][edge.Bz].transform.position;
                var alongX = edge.Az != edge.Bz;
                if (FillEdgePlan.LiesOnEdge((a.x + b.x) / 2, (a.z + b.z) / 2, alongX, tileWidth / 2, position.x, position.z))
                {
                    stale.Add(piece);
                    break;
                }
            }
        }

        foreach (var piece in stale)
        {
            tileGen.fillTiles.Remove(piece);
            piece.SetActive(false);
            UnityEngine.Object.Destroy(piece);
        }

        return stale.Count;
    }

    private static void Build(ProceduralTileGeneration tileGen, Vector2Int from, Vector2Int to, MelonLogger.Instance logger)
    {
        try
        {
            FillHole.Invoke(tileGen, new object[] { from, to });
        }
        catch (Exception ex)
        {
            logger.Warning($"FillRegeneration: FillHole({from}, {to}) failed: {ex.InnerException?.Message ?? ex.Message}");
        }
    }
}
