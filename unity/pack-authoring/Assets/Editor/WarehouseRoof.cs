using System;
using System.Collections.Generic;
using System.Numerics;

// Pure geometry with no Unity types, so the unit tests can compile it directly. Units are whatever the caller uses; the Warehouse build passes mesh space.
public static class WarehouseRoof
{
    // Index into the per-side arrays; the west and east sides run along z, the south and north sides along x.
    public enum Side { West, East, South, North }

    // Per cell along one edge: the highest vertex of any steep face (normal within 60 degrees of horizontal) lying within band of the edge plane, or floorY where no wall stands there.
    public static float[] EdgeWallTops(IEnumerable<Vector3[]> triangles, Side side, float alongMin, float alongMax, float planeCoord, float cell, float band, float floorY)
    {
        var tops = new float[Math.Max(1, (int)MathF.Ceiling((alongMax - alongMin) / cell))];
        Array.Fill(tops, floorY);
        var alongX = side is Side.South or Side.North;
        foreach (var t in triangles)
        {
            var normal = Vector3.Cross(t[1] - t[0], t[2] - t[0]);
            if (normal.Length() == 0 || MathF.Abs(normal.Y) / normal.Length() >= 0.5f)
                continue;
            float Across(Vector3 p) => alongX ? p.Z : p.X;
            float Along(Vector3 p) => alongX ? p.X : p.Z;
            if (Array.Exists(t, p => MathF.Abs(Across(p) - planeCoord) > band))
                continue;
            var top = MathF.Max(t[0].Y, MathF.Max(t[1].Y, t[2].Y));
            var first = Math.Clamp((int)MathF.Floor((MathF.Min(Along(t[0]), MathF.Min(Along(t[1]), Along(t[2]))) - alongMin) / cell), 0, tops.Length - 1);
            var last = Math.Clamp((int)MathF.Floor((MathF.Max(Along(t[0]), MathF.Max(Along(t[1]), Along(t[2]))) - alongMin) / cell), 0, tops.Length - 1);
            for (var i = first; i <= last; i++)
                tops[i] = MathF.Max(tops[i], top);
        }

        return tops;
    }

    // One flat down-facing roof over the footprint at roofY, and an inward-facing skirt per edge cell from that cell's wall top up to the roof, so no gap is left between the walls and the roof. The edges sit inset inside the footprint. wallTops holds one array per Side. Front faces follow Unity's clockwise-from-front rule (cross(b - a, c - a) is the front normal).
    public static IEnumerable<Vector3[]> Quads(float roofY, float minX, float minZ, float maxX, float maxZ, float cell, float inset, float[][] wallTops)
    {
        float x0 = minX + inset, x1 = maxX - inset, z0 = minZ + inset, z1 = maxZ - inset;
        var inside = new Vector3((x0 + x1) / 2, roofY - 1, (z0 + z1) / 2);
        yield return Facing(new Vector3(x0, roofY, z0), new Vector3(x1, roofY, z0), new Vector3(x1, roofY, z1), new Vector3(x0, roofY, z1), inside);
        foreach (var side in new[] { Side.West, Side.East, Side.South, Side.North })
        {
            var alongX = side is Side.South or Side.North;
            var tops = wallTops[(int)side];
            float alongMin = alongX ? minX : minZ, alongMax = alongX ? maxX : maxZ;
            var plane = side switch { Side.West => x0, Side.East => x1, Side.South => z0, _ => z1 };
            var cells = Math.Min(tops.Length, (int)MathF.Ceiling((alongMax - alongMin) / cell));
            for (var i = 0; i < cells; i++)
            {
                if (tops[i] >= roofY)
                    continue;
                float a0 = alongMin + i * cell, a1 = MathF.Min(a0 + cell, alongMax);
                var (start, end) = alongX ? (new Vector3(a0, 0, plane), new Vector3(a1, 0, plane)) : (new Vector3(plane, 0, a0), new Vector3(plane, 0, a1));
                var a = new Vector3(start.X, tops[i], start.Z);
                var b = new Vector3(start.X, roofY, start.Z);
                var c = new Vector3(end.X, roofY, end.Z);
                var d = new Vector3(end.X, tops[i], end.Z);
                yield return Facing(a, b, c, d, new Vector3((x0 + x1) / 2, (tops[i] + roofY) / 2, (z0 + z1) / 2));
            }
        }
    }

    static Vector3[] Facing(Vector3 a, Vector3 b, Vector3 c, Vector3 d, Vector3 towards)
    {
        var normal = Vector3.Cross(b - a, c - a);
        return Vector3.Dot(normal, towards - a) >= 0 ? new[] { a, b, c, d } : new[] { d, c, b, a };
    }
}
