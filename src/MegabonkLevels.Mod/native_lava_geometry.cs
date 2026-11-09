using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

public static class NativeLavaGeometry
{
    public static IReadOnlyList<int> FaceUp(IReadOnlyList<Vector3Data> vertices, IReadOnlyList<int> triangles)
    {
        var result = triangles.ToArray();
        for (var i = 0; i < result.Length; i += 3)
        {
            var a = vertices[result[i]];
            var b = vertices[result[i + 1]];
            var c = vertices[result[i + 2]];
            var up = (b.Z - a.Z) * (c.X - a.X) - (b.X - a.X) * (c.Z - a.Z);
            if (up < 0) (result[i + 1], result[i + 2]) = (result[i + 2], result[i + 1]);
        }
        return result;
    }

    public static bool CanFit(IReadOnlyList<Vector3Data> vertices)
    {
        if (vertices.Count < 4 || vertices.Any(v => !float.IsFinite(v.X) || !float.IsFinite(v.Y) || !float.IsFinite(v.Z))) return false;
        var minX = vertices.Min(v => v.X);
        var maxX = vertices.Max(v => v.X);
        var minZ = vertices.Min(v => v.Z);
        var maxZ = vertices.Max(v => v.Z);
        if (maxX - minX < 0.001f || maxZ - minZ < 0.001f || vertices.Max(v => v.Y) - vertices.Min(v => v.Y) > 0.01f) return false;
        if (vertices.Any(v => MathF.Min(MathF.Abs(v.X - minX), MathF.Abs(v.X - maxX)) > 0.001f
            || MathF.Min(MathF.Abs(v.Z - minZ), MathF.Abs(v.Z - maxZ)) > 0.001f)) return false;
        return vertices.Select(v => (v.X > (minX + maxX) / 2, v.Z > (minZ + maxZ) / 2)).Distinct().Count() == 4;
    }

    public static IReadOnlyList<Vector3Data> Fit(IReadOnlyList<Vector3Data> vertices, Vector3Data center, float width, float depth)
    {
        if (!CanFit(vertices)) throw new ArgumentException("Native lava template must be a flat rectangular surface.");
        var minX = vertices.Min(v => v.X);
        var spanX = vertices.Max(v => v.X) - minX;
        var minZ = vertices.Min(v => v.Z);
        var spanZ = vertices.Max(v => v.Z) - minZ;
        return vertices.Select(v => new Vector3Data(center.X + ((v.X - minX) / spanX - 0.5f) * width,
            center.Y, center.Z + ((v.Z - minZ) / spanZ - 0.5f) * depth)).ToList();
    }
}
