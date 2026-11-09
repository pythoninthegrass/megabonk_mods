using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UnityEngine;

namespace MegabonkLevels;

// Rebuild only edited edges; whole-grid FillHoles/FillEdges would duplicate untouched pieces.
public static class FillRegeneration
{
    private static readonly MethodInfo FillHole = typeof(ProceduralTileGeneration).GetMethod(
        "FillHole", BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public);
    private static readonly MethodInfo FillEdge = typeof(ProceduralTileGeneration).GetMethod(
        "FillEdge", BindingFlags.Instance | BindingFlags.NonPublic | BindingFlags.Public);

    public static void Regenerate(ProceduralTileGeneration tileGen, float tileWidth, IEnumerable<(int X, int Z)> touched, ModLogger logger, bool includeExterior = false)
    {
        if (FillHole == null || FillEdge == null)
        {
            logger.Warning("FillRegeneration: FillHole or FillEdge not found; wall and fill pieces left as they were");
            return;
        }

        var grid = tileGen.proceduralTiles;
        bool InGrid(int x, int z) => x >= 0 && x < grid.Length && grid[x] != null && z >= 0 && z < grid[x].Length;
        bool Occupied(int x, int z) => InGrid(x, z) && grid[x][z] != null;
        var cells = touched.ToList();
        var edges = FillEdgePlan.EdgesAround(cells, Occupied);
        var holeEdges = includeExterior
            ? FillEdgePlan.ExposedEdges(cells, Occupied)
            : FillEdgePlan.EdgesAroundRemovals(cells, Occupied, InGrid);
        var cleanup = FillEdgePlan.CleanupEdges(cells, Occupied, InGrid);

        var removed = RemoveStalePieces(tileGen, tileWidth, cleanup);
        var before = tileGen.fillTiles.Count;
        foreach (var edge in edges)
        {
            Build(tileGen, new Vector2Int(edge.Ax, edge.Az), new Vector2Int(edge.Bx, edge.Bz), logger);
            Build(tileGen, new Vector2Int(edge.Bx, edge.Bz), new Vector2Int(edge.Ax, edge.Az), logger);
        }

        var minimumHeight = int.MaxValue;
        for (var x = 0; x < grid.Length; x++)
        {
            for (var z = 0; grid[x] != null && z < grid[x].Length; z++)
            {
                if (grid[x][z] != null)
                {
                    minimumHeight = Math.Min(minimumHeight, grid[x][z].posY);
                }
            }
        }

        foreach (var edge in holeEdges)
        {
            var a = new Vector2Int(edge.Ax, edge.Az);
            var b = new Vector2Int(edge.Bx, edge.Bz);
            var from = Occupied(edge.Ax, edge.Az) ? a : b;
            var to = from == a ? b : a;
            var offset = FillEdgePlan.HoleWallOffset(minimumHeight, grid[from.x][from.y].posY);
            try
            {
                FillEdge.Invoke(tileGen, new object[] { from, offset, true, to - from, false });
            }
            catch (Exception ex)
            {
                logger.Warning($"FillRegeneration: FillEdge({from}, {offset}, {to - from}) failed: {ex.InnerException?.Message ?? ex.Message}");
            }
        }

        logger.Msg($"FillRegeneration: {edges.Count} edge(s), {holeEdges.Count} hole edge(s), removed {removed} stale piece(s), created {tileGen.fillTiles.Count - before}");
    }

    private static int RemoveStalePieces(ProceduralTileGeneration tileGen, float tileWidth, IReadOnlyList<CellEdge> edges)
    {
        var origin = tileGen.TilePositionToWorldPosition(Vector2Int.zero);
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
                var mx = origin.x + (edge.Ax + edge.Bx) * tileWidth / 2;
                var mz = origin.z + (edge.Az + edge.Bz) * tileWidth / 2;
                var alongX = edge.Az != edge.Bz;
                if (FillEdgePlan.LiesOnEdge(mx, mz, alongX, tileWidth / 2, position.x, position.z))
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

    private static void Build(ProceduralTileGeneration tileGen, Vector2Int from, Vector2Int to, ModLogger logger)
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
