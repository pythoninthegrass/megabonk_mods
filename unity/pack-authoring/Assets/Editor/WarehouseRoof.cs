using System;
using System.Collections.Generic;
using System.Linq;
using System.Numerics;

// Pure geometry with no Unity types, so the unit tests can compile it directly. Units are whatever the caller uses; the Warehouse build passes mesh space.
public static class WarehouseRoof
{
    const float Epsilon = 1e-5f;

    // Index into the per-side arrays; the west and east sides run along z, the south and north sides along x.
    public enum Side { West, East, South, North }

    // The wall-top line along one edge as (along, y) points in order: for every stretch between vertices of the steep faces (normal within 60 degrees of horizontal) lying within band of the edge plane, the covering face's top at both ends, or floorY where no wall stands. The line never rises above a wall, and steps where heights jump.
    public static Vector2[] EdgeWallProfile(IEnumerable<Vector3[]> triangles, Side side, float alongMin, float alongMax, float planeCoord, float band, float floorY)
    {
        var alongX = side is Side.South or Side.North;
        var walls = new List<Vector2[]>();
        foreach (var t in triangles)
        {
            var normal = Vector3.Cross(t[1] - t[0], t[2] - t[0]);
            if (normal.Length() == 0 || MathF.Abs(normal.Y) / normal.Length() >= 0.5f)
                continue;
            if (Array.Exists(t, p => MathF.Abs((alongX ? p.Z : p.X) - planeCoord) > band))
                continue;
            walls.Add(Array.ConvertAll(t, p => new Vector2(alongX ? p.X : p.Z, p.Y)));
        }

        var breaks = walls.SelectMany(w => w).Select(p => Math.Clamp(p.X, alongMin, alongMax)).Append(alongMin).Append(alongMax).OrderBy(a => a).ToList();
        var profile = new List<Vector2>();
        for (var i = 0; i + 1 < breaks.Count; i++)
        {
            float a0 = breaks[i], a1 = breaks[i + 1];
            if (a1 - a0 < Epsilon)
                continue;
            var (y0, y1) = (floorY, floorY);
            var best = float.NegativeInfinity;
            foreach (var w in walls)
            {
                if (w.Min(p => p.X) > a0 + Epsilon || w.Max(p => p.X) < a1 - Epsilon)
                    continue;
                var (top0, top1) = (MathF.Max(floorY, TopAt(w, a0)), MathF.Max(floorY, TopAt(w, a1)));
                if (top0 + top1 > best)
                    (best, y0, y1) = (top0 + top1, top0, top1);
            }

            AddDistinct(profile, new Vector2(a0, y0));
            AddDistinct(profile, new Vector2(a1, y1));
        }

        return profile.ToArray();
    }

    // Highest surface height over every grid cell, or NaN where nothing is over it. A face that is not steep is sampled across each cell it covers; a steep face (a wall) is traced along its base line so its top reaches every cell it passes through.
    public static float[,] ColumnTops(IEnumerable<Vector3[]> triangles, float minX, float minZ, float cell, int cellsX, int cellsZ)
    {
        var tops = new float[cellsX, cellsZ];
        for (var i = 0; i < cellsX; i++)
            for (var j = 0; j < cellsZ; j++)
                tops[i, j] = float.NaN;
        void Put(float x, float z, float y)
        {
            int i = (int)MathF.Floor((x - minX) / cell), j = (int)MathF.Floor((z - minZ) / cell);
            if (i >= 0 && i < cellsX && j >= 0 && j < cellsZ && !(y <= tops[i, j]))
                tops[i, j] = y;
        }

        foreach (var t in triangles)
        {
            foreach (var p in t)
                Put(p.X, p.Z, p.Y);
            var normal = Vector3.Cross(t[1] - t[0], t[2] - t[0]);
            if (normal.Length() == 0)
                continue;
            if (MathF.Abs(normal.Y) / normal.Length() >= 0.5f)
            {
                int first = (int)MathF.Floor((t.Min(p => p.X) - minX) / cell), last = (int)MathF.Floor((t.Max(p => p.X) - minX) / cell);
                int firstZ = (int)MathF.Floor((t.Min(p => p.Z) - minZ) / cell), lastZ = (int)MathF.Floor((t.Max(p => p.Z) - minZ) / cell);
                for (var i = Math.Max(0, first); i <= Math.Min(cellsX - 1, last); i++)
                    for (var j = Math.Max(0, firstZ); j <= Math.Min(cellsZ - 1, lastZ); j++)
                        foreach (var fx in new[] { 0.1f, 0.5f, 0.9f })
                            foreach (var fz in new[] { 0.1f, 0.5f, 0.9f })
                            {
                                float x = minX + (i + fx) * cell, z = minZ + (j + fz) * cell;
                                var y = HeightInside(t, normal, x, z);
                                if (!float.IsNaN(y))
                                    Put(x, z, y);
                            }
            }
            else
            {
                TraceWall(t, cell, Put);
            }
        }

        return tops;
    }

    // Level each cell would fill to if water poured over the rim from outside: the lowest height over which a player in it could clear every wall around it, never below its own surface. Boundary cells at or below openBelow have nothing built there and start at sealY; the rest start at their own height.
    public static float[,] SpillLevels(float[,] tops, float openBelow, float sealY)
    {
        int cellsX = tops.GetLength(0), cellsZ = tops.GetLength(1);
        float Surface(int i, int j) => float.IsNaN(tops[i, j]) ? 0 : tops[i, j];
        var level = new float[cellsX, cellsZ];
        for (var i = 0; i < cellsX; i++)
            for (var j = 0; j < cellsZ; j++)
                level[i, j] = float.PositiveInfinity;
        var queue = new SortedSet<(float Level, int Index)>();
        for (var i = 0; i < cellsX; i++)
            for (var j = 0; j < cellsZ; j++)
                if (i == 0 || j == 0 || i == cellsX - 1 || j == cellsZ - 1)
                {
                    level[i, j] = Surface(i, j) > openBelow ? Surface(i, j) : sealY;
                    queue.Add((level[i, j], i * cellsZ + j));
                }

        while (queue.Count > 0)
        {
            var (water, index) = queue.Min;
            queue.Remove(queue.Min);
            int ci = index / cellsZ, cj = index % cellsZ;
            foreach (var (di, dj) in new[] { (1, 0), (-1, 0), (0, 1), (0, -1) })
            {
                int i = ci + di, j = cj + dj;
                if (i < 0 || j < 0 || i >= cellsX || j >= cellsZ)
                    continue;
                var offered = MathF.Max(Surface(i, j), water);
                if (offered >= level[i, j])
                    continue;
                queue.Remove((level[i, j], i * cellsZ + j));
                level[i, j] = offered;
                queue.Add((offered, i * cellsZ + j));
            }
        }

        return level;
    }

    // Down-facing roof quads (equal-height cells in a row merged), a vertical step face between cells of different height facing the taller side, and an inward-facing skirt per wall-profile segment and cell along each outer edge, from the wall-top line up to that edge cell's ceiling. The outer edges sit inset inside the footprint. profiles holds one EdgeWallProfile per Side. Front faces follow Unity's clockwise-from-front rule (cross(b - a, c - a) is the front normal).
    public static IEnumerable<Vector3[]> Quads(float[,] ceiling, float minX, float minZ, float maxX, float maxZ, float cell, float inset, Vector2[][] profiles)
    {
        int cellsX = ceiling.GetLength(0), cellsZ = ceiling.GetLength(1);
        float EdgeX(int i) => i == 0 ? minX + inset : i == cellsX ? maxX - inset : MathF.Min(minX + i * cell, maxX);
        float EdgeZ(int j) => j == 0 ? minZ + inset : j == cellsZ ? maxZ - inset : MathF.Min(minZ + j * cell, maxZ);
        for (var j = 0; j < cellsZ; j++)
        {
            for (var i = 0; i < cellsX;)
            {
                var run = i;
                while (run + 1 < cellsX && ceiling[run + 1, j] == ceiling[i, j])
                    run++;
                float x0 = EdgeX(i), x1 = EdgeX(run + 1), z0 = EdgeZ(j), z1 = EdgeZ(j + 1), y = ceiling[i, j];
                yield return Facing(new Vector3(x0, y, z0), new Vector3(x1, y, z0), new Vector3(x1, y, z1), new Vector3(x0, y, z1), new Vector3((x0 + x1) / 2, y - 1, (z0 + z1) / 2));
                i = run + 1;
            }

            for (var i = 0; i < cellsX; i++)
            {
                float x0 = EdgeX(i), x1 = EdgeX(i + 1), z0 = EdgeZ(j), z1 = EdgeZ(j + 1);
                if (i + 1 < cellsX && ceiling[i + 1, j] != ceiling[i, j])
                    yield return Step(new Vector3(x1, 0, z0), new Vector3(x1, 0, z1), ceiling[i, j], ceiling[i + 1, j], new Vector3(x1 + (ceiling[i, j] > ceiling[i + 1, j] ? -1 : 1), 0, 0));
                if (j + 1 < cellsZ && ceiling[i, j + 1] != ceiling[i, j])
                    yield return Step(new Vector3(x0, 0, z1), new Vector3(x1, 0, z1), ceiling[i, j], ceiling[i, j + 1], new Vector3(0, 0, z1 + (ceiling[i, j] > ceiling[i, j + 1] ? -1 : 1)));
            }
        }

        float x0In = minX + inset, x1In = maxX - inset, z0In = minZ + inset, z1In = maxZ - inset;
        var inside = new Vector3((x0In + x1In) / 2, 0, (z0In + z1In) / 2);
        foreach (var side in new[] { Side.West, Side.East, Side.South, Side.North })
        {
            var alongX = side is Side.South or Side.North;
            var profile = profiles[(int)side];
            var plane = side switch { Side.West => x0In, Side.East => x1In, Side.South => z0In, _ => z1In };
            var cells = alongX ? cellsX : cellsZ;
            float CellStart(int k) => (alongX ? minX : minZ) + k * cell;
            float EdgeCeiling(int k) => side switch { Side.West => ceiling[0, k], Side.East => ceiling[cellsX - 1, k], Side.South => ceiling[k, 0], _ => ceiling[k, cellsZ - 1] };
            for (var n = 0; n + 1 < profile.Length; n++)
            {
                Vector2 p = profile[n], q = profile[n + 1];
                if (q.X - p.X < Epsilon)
                    continue;
                for (var k = 0; k < cells; k++)
                {
                    float a0 = MathF.Max(p.X, CellStart(k)), a1 = MathF.Min(q.X, k + 1 == cells ? float.PositiveInfinity : CellStart(k + 1));
                    if (a1 - a0 < Epsilon)
                        continue;
                    float Bottom(float along) => p.Y + (q.Y - p.Y) * (along - p.X) / (q.X - p.X);
                    float top = EdgeCeiling(k), b0 = MathF.Min(Bottom(a0), top), b1 = MathF.Min(Bottom(a1), top);
                    if (b0 >= top && b1 >= top)
                        continue;
                    Vector3 At(float along, float y) => alongX ? new Vector3(along, y, plane) : new Vector3(plane, y, along);
                    yield return Facing(At(a0, b0), At(a0, top), At(a1, top), At(a1, b1), new Vector3(inside.X, (b0 + top) / 2, inside.Z));
                }
            }
        }
    }

    // Highest point of the triangle on the vertical line at along, taken over its edges.
    static float TopAt(Vector2[] triangle, float along)
    {
        var top = float.NegativeInfinity;
        for (var i = 0; i < 3; i++)
        {
            Vector2 p = triangle[i], q = triangle[(i + 1) % 3];
            if (MathF.Abs(q.X - p.X) < Epsilon)
            {
                if (MathF.Abs(p.X - along) < Epsilon)
                    top = MathF.Max(top, MathF.Max(p.Y, q.Y));
            }
            else if (along >= MathF.Min(p.X, q.X) - Epsilon && along <= MathF.Max(p.X, q.X) + Epsilon)
            {
                top = MathF.Max(top, p.Y + (q.Y - p.Y) * (along - p.X) / (q.X - p.X));
            }
        }

        return top;
    }

    static void AddDistinct(List<Vector2> points, Vector2 point)
    {
        if (points.Count == 0 || points[^1] != point)
            points.Add(point);
    }

    static Vector3[] Facing(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 towards)
    {
        var normal = Vector3.Cross(b - a, c - a);
        return Vector3.Dot(normal, towards - a) >= 0 ? new[] { a, b, c, d } : new[] { d, c, b, a };
    }

    // A vertical quad over start-end between two heights, wound so its front faces the point towards (compared on the axis the wall is perpendicular to).
    static Vector3[] Step(Vector3 start, Vector3 end, float heightHere, float heightThere, Vector3 towards)
    {
        float low = MathF.Min(heightHere, heightThere), high = MathF.Max(heightHere, heightThere);
        var a = new Vector3(start.X, low, start.Z);
        var b = new Vector3(start.X, high, start.Z);
        var c = new Vector3(end.X, high, end.Z);
        var d = new Vector3(end.X, low, end.Z);
        var probe = new Vector3(towards.X == 0 ? start.X : towards.X, (low + high) / 2, towards.Z == 0 ? start.Z : towards.Z);
        return Facing(a, b, c, d, probe);
    }

    // Height of a non-steep triangle over (x, z), or NaN when the point is outside it.
    static float HeightInside(Vector3[] t, Vector3 normal, float x, float z)
    {
        float Side(Vector3 p, Vector3 q) => (x - q.X) * (p.Z - q.Z) - (p.X - q.X) * (z - q.Z);
        float d1 = Side(t[0], t[1]), d2 = Side(t[1], t[2]), d3 = Side(t[2], t[0]);
        if ((d1 < 0 || d2 < 0 || d3 < 0) && (d1 > 0 || d2 > 0 || d3 > 0))
            return float.NaN;
        return t[0].Y - (normal.X * (x - t[0].X) + normal.Z * (z - t[0].Z)) / normal.Y;
    }

    // Walks a steep triangle's base line (its two farthest-apart corners, seen from above) in steps well under a cell, handing each point the triangle's top over it.
    static void TraceWall(Vector3[] t, float cell, Action<float, float, float> put)
    {
        var (p0, p1) = (t[0], t[1]);
        var longest = -1f;
        for (var a = 0; a < 3; a++)
            for (var b = a + 1; b < 3; b++)
            {
                var d = new Vector2(t[b].X - t[a].X, t[b].Z - t[a].Z).Length();
                if (d > longest)
                    (longest, p0, p1) = (d, t[a], t[b]);
            }

        if (longest < Epsilon)
            return;
        var direction = new Vector2(p1.X - p0.X, p1.Z - p0.Z) / longest;
        var profile = Array.ConvertAll(t, p => new Vector2((p.X - p0.X) * direction.X + (p.Z - p0.Z) * direction.Y, p.Y));
        var steps = (int)MathF.Ceiling(longest / (cell / 3)) + 1;
        for (var k = 0; k <= steps; k++)
        {
            var along = longest * k / steps;
            var y = TopAt(profile, along);
            if (!float.IsNegativeInfinity(y))
                put(p0.X + direction.X * along, p0.Z + direction.Y * along, y);
        }
    }
}
