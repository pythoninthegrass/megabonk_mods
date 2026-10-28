using System;
using System.Collections.Generic;
using System.Numerics;

// Pure geometry with no Unity types, so the unit tests can compile it directly. Units are whatever the caller uses; the Warehouse build passes mesh space.
public static class WarehouseRoof
{
    // Highest standable surface touching each cell, or NaN where none does. A triangle is standable when its normal is within 60 degrees of vertical (either way, since the collider is two-sided).
    public static float[,] CellTops(IEnumerable<Vector3[]> triangles, float minX, float minZ, float cell, int cellsX, int cellsZ)
    {
        var tops = new float[cellsX, cellsZ];
        for (var i = 0; i < cellsX; i++)
            for (var j = 0; j < cellsZ; j++)
                tops[i, j] = float.NaN;
        foreach (var t in triangles)
        {
            var normal = Vector3.Cross(t[1] - t[0], t[2] - t[0]);
            if (normal.Length() == 0 || MathF.Abs(normal.Y) / normal.Length() < 0.5f)
                continue;
            var top = MathF.Max(t[0].Y, MathF.Max(t[1].Y, t[2].Y));
            var first = ClampCell((MathF.Min(t[0].X, MathF.Min(t[1].X, t[2].X)) - minX) / cell, cellsX);
            var last = ClampCell((MathF.Max(t[0].X, MathF.Max(t[1].X, t[2].X)) - minX) / cell, cellsX);
            var firstZ = ClampCell((MathF.Min(t[0].Z, MathF.Min(t[1].Z, t[2].Z)) - minZ) / cell, cellsZ);
            var lastZ = ClampCell((MathF.Max(t[0].Z, MathF.Max(t[1].Z, t[2].Z)) - minZ) / cell, cellsZ);
            for (var i = first; i <= last; i++)
                for (var j = firstZ; j <= lastZ; j++)
                    if (Touches(t, minX + i * cell, minZ + j * cell, cell) && (float.IsNaN(tops[i, j]) || top > tops[i, j]))
                        tops[i, j] = top;
        }

        return tops;
    }

    // Per cell: the tallest top within reachCells (Chebyshev) plus clearance; a cell with no top in reach uses the tallest top anywhere.
    public static float[,] RoofHeights(float[,] tops, int reachCells, float clearance)
    {
        int cellsX = tops.GetLength(0), cellsZ = tops.GetLength(1);
        var tallest = float.NegativeInfinity;
        foreach (var top in tops)
            if (!float.IsNaN(top))
                tallest = MathF.Max(tallest, top);
        var roof = new float[cellsX, cellsZ];
        for (var i = 0; i < cellsX; i++)
            for (var j = 0; j < cellsZ; j++)
            {
                var best = float.NegativeInfinity;
                for (var a = Math.Max(0, i - reachCells); a <= Math.Min(cellsX - 1, i + reachCells); a++)
                    for (var b = Math.Max(0, j - reachCells); b <= Math.Min(cellsZ - 1, j + reachCells); b++)
                        if (!float.IsNaN(tops[a, b]))
                            best = MathF.Max(best, tops[a, b]);
                roof[i, j] = (float.IsNegativeInfinity(best) ? tallest : best) + clearance;
            }

        return roof;
    }

    // A down-facing roof quad per cell, a vertical step face between cells of different height (facing the taller cell, which is the side with air under it), and an inward-facing skirt on each outer edge cell from skirtBottom up to the roof where the roof is higher. The outer edges sit inset inside the footprint. Front faces follow Unity's clockwise-from-front rule (cross(b - a, c - a) is the front normal).
    public static IEnumerable<Vector3[]> Quads(float[,] roof, float minX, float minZ, float maxX, float maxZ, float cell, float skirtBottom, float inset)
    {
        int cellsX = roof.GetLength(0), cellsZ = roof.GetLength(1);
        float EdgeX(int i) => i == 0 ? minX + inset : i == cellsX ? maxX - inset : MathF.Min(minX + i * cell, maxX);
        float EdgeZ(int j) => j == 0 ? minZ + inset : j == cellsZ ? maxZ - inset : MathF.Min(minZ + j * cell, maxZ);
        for (var i = 0; i < cellsX; i++)
            for (var j = 0; j < cellsZ; j++)
            {
                float x0 = EdgeX(i), x1 = EdgeX(i + 1), z0 = EdgeZ(j), z1 = EdgeZ(j + 1), y = roof[i, j];
                var below = new Vector3((x0 + x1) / 2, y - 1, (z0 + z1) / 2);
                yield return Facing(new Vector3(x0, y, z0), new Vector3(x1, y, z0), new Vector3(x1, y, z1), new Vector3(x0, y, z1), below);
                if (i + 1 < cellsX && roof[i + 1, j] != y)
                    yield return Step(new Vector3(x1, 0, z0), new Vector3(x1, 0, z1), y, roof[i + 1, j], true);
                if (j + 1 < cellsZ && roof[i, j + 1] != y)
                    yield return Step(new Vector3(x0, 0, z1), new Vector3(x1, 0, z1), y, roof[i, j + 1], false);
                if (i == 0 && y > skirtBottom)
                    yield return Skirt(new Vector3(x0, 0, z0), new Vector3(x0, 0, z1), skirtBottom, y, new Vector3(x0 + 1, 0, 0));
                if (i == cellsX - 1 && y > skirtBottom)
                    yield return Skirt(new Vector3(x1, 0, z0), new Vector3(x1, 0, z1), skirtBottom, y, new Vector3(x1 - 1, 0, 0));
                if (j == 0 && y > skirtBottom)
                    yield return Skirt(new Vector3(x0, 0, z0), new Vector3(x1, 0, z0), skirtBottom, y, new Vector3(0, 0, z0 + 1));
                if (j == cellsZ - 1 && y > skirtBottom)
                    yield return Skirt(new Vector3(x0, 0, z1), new Vector3(x1, 0, z1), skirtBottom, y, new Vector3(0, 0, z1 - 1));
            }
    }

    static Vector3[] Step(Vector3 start, Vector3 end, float heightHere, float heightThere, bool acrossX)
    {
        var low = MathF.Min(heightHere, heightThere);
        var high = MathF.Max(heightHere, heightThere);
        var taller = heightHere > heightThere ? -1f : 1f;
        var toward = acrossX ? new Vector3(start.X + taller, 0, 0) : new Vector3(0, 0, start.Z + taller);
        return Skirt(start, end, low, high, toward);
    }

    // A vertical quad over start-end between two heights, wound so its front faces the point towards (compared on the axis the wall is perpendicular to).
    static Vector3[] Skirt(Vector3 start, Vector3 end, float low, float high, Vector3 towards)
    {
        var a = new Vector3(start.X, low, start.Z);
        var b = new Vector3(start.X, high, start.Z);
        var c = new Vector3(end.X, high, end.Z);
        var d = new Vector3(end.X, low, end.Z);
        var probe = new Vector3(towards.X == 0 ? start.X : towards.X, (low + high) / 2, towards.Z == 0 ? start.Z : towards.Z);
        return Facing(a, b, c, d, probe);
    }

    static Vector3[] Facing(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 towards)
    {
        var normal = Vector3.Cross(b - a, c - a);
        return Vector3.Dot(normal, towards - a) >= 0 ? new[] { a, b, c, d } : new[] { d, c, b, a };
    }

    static int ClampCell(float position, int cells) => Math.Clamp((int)MathF.Floor(position), 0, cells - 1);

    static bool Touches(Vector3[] t, float x, float z, float cell)
    {
        foreach (var p in t)
            if (p.X >= x && p.X <= x + cell && p.Z >= z && p.Z <= z + cell)
                return true;
        foreach (var fx in new[] { 0f, 0.5f, 1f })
            foreach (var fz in new[] { 0f, 0.5f, 1f })
                if (InsideXZ(t, x + fx * cell, z + fz * cell))
                    return true;
        return false;
    }

    static bool InsideXZ(Vector3[] t, float x, float z)
    {
        float Side(Vector3 p, Vector3 q) => (x - q.X) * (p.Z - q.Z) - (p.X - q.X) * (z - q.Z);
        float d1 = Side(t[0], t[1]), d2 = Side(t[1], t[2]), d3 = Side(t[2], t[0]);
        return !((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0));
    }
}
