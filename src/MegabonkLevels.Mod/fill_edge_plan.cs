using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// An unordered pair of adjacent grid cells, stored with (Ax, Az) sorting before (Bx, Bz).
public readonly record struct CellEdge(int Ax, int Az, int Bx, int Bz);

// Which cell-to-cell edges need their wall and fill pieces regenerated after tiles were edited, and which live
// pieces sit on an edge. Pure so it can be tested without the game.
public static class FillEdgePlan
{
    private const float LineTolerance = 0.5f;

    private static readonly (int Dx, int Dz)[] Neighbours = { (-1, 0), (1, 0), (0, -1), (0, 1) };

    public static IReadOnlyList<CellEdge> EdgesAroundRemovals(IEnumerable<(int X, int Z)> touched,
        Func<int, int, bool> isOccupied, Func<int, int, bool> isInGrid) =>
        CleanupEdges(touched, isOccupied, isInGrid)
            .Where(e => isInGrid(e.Ax, e.Az) && isInGrid(e.Bx, e.Bz)
                && isOccupied(e.Ax, e.Az) != isOccupied(e.Bx, e.Bz)).ToList();

    // Empty touched cells need every old edge cleared, including shared holes and the outer border.
    public static IReadOnlyList<CellEdge> CleanupEdges(IEnumerable<(int X, int Z)> touched,
        Func<int, int, bool> isOccupied, Func<int, int, bool> isInGrid)
    {
        var edges = new HashSet<CellEdge>();
        foreach (var (x, z) in touched.Distinct().Where(p => isInGrid(p.X, p.Z)))
        {
            foreach (var (dx, dz) in Neighbours)
            {
                var (nx, nz) = (x + dx, z + dz);
                if (!isOccupied(x, z) || isInGrid(nx, nz))
                {
                    edges.Add((x, z).CompareTo((nx, nz)) < 0
                        ? new CellEdge(x, z, nx, nz) : new CellEdge(nx, nz, x, z));
                }
            }
        }

        return edges.OrderBy(e => (e.Ax, e.Az, e.Bx, e.Bz)).ToList();
    }

    public static int HoleWallOffset(int minimumHeight, int tileHeight) => minimumHeight - 1 - tileHeight;

    public static IReadOnlyList<CellEdge> ExposedEdges(IEnumerable<(int X, int Z)> cells, Func<int, int, bool> isOccupied)
    {
        var edges = new HashSet<CellEdge>();
        foreach (var (x, z) in cells.Distinct().Where(p => isOccupied(p.X, p.Z)))
        {
            foreach (var (dx, dz) in Neighbours)
            {
                var next = (X: x + dx, Z: z + dz);
                if (!isOccupied(next.X, next.Z))
                {
                    edges.Add((x, z).CompareTo(next) < 0
                        ? new CellEdge(x, z, next.X, next.Z) : new CellEdge(next.X, next.Z, x, z));
                }
            }
        }

        return edges.OrderBy(e => (e.Ax, e.Az, e.Bx, e.Bz)).ToList();
    }

    // Edges between a touched, occupied cell and an occupied neighbour. A neighbour that is empty or outside the
    // grid has no tile to wall against, so that edge is left alone.
    public static IReadOnlyList<CellEdge> EdgesAround(IEnumerable<(int X, int Z)> touched, Func<int, int, bool> isOccupied)
    {
        var edges = new SortedSet<CellEdge>(Comparer<CellEdge>.Create((a, b) =>
            (a.Ax, a.Az, a.Bx, a.Bz).CompareTo((b.Ax, b.Az, b.Bx, b.Bz))));

        foreach (var (x, z) in touched.Distinct())
        {
            if (!isOccupied(x, z))
            {
                continue;
            }

            foreach (var (dx, dz) in Neighbours)
            {
                var (nx, nz) = (x + dx, z + dz);
                if (!isOccupied(nx, nz))
                {
                    continue;
                }

                edges.Add((x, z).CompareTo((nx, nz)) < 0 ? new CellEdge(x, z, nx, nz) : new CellEdge(nx, nz, x, z));
            }
        }

        return edges.ToList();
    }

    // True when a piece at (px, pz) lies on the edge whose midpoint is (mx, mz): on the edge line, within half the
    // edge length either side of the midpoint. alongX is true for an edge that runs along the world X axis.
    public static bool LiesOnEdge(float mx, float mz, bool alongX, float halfLength, float px, float pz)
    {
        var (along, across) = alongX ? (px - mx, pz - mz) : (pz - mz, px - mx);
        return Math.Abs(across) <= LineTolerance && Math.Abs(along) <= halfLength + LineTolerance;
    }
}
