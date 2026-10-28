using System;
using System.Collections.Generic;
using System.Numerics;

// Pure geometry with no Unity types, so the unit tests can compile it directly.
public static class CoplanarLayering
{
    // Mesh-space distance each stacked face is lifted along its normal.
    public const float LiftStep = 0.0005f;

    const float PlaneTolerance = 0.00001f;
    const float SameFacingDot = 0.9999f;
    const float OverlapEpsilon = 0.000001f;

    // Each face is a list of corner indices in OBJ order, with corners not shared between faces. The front normal is that of the reversed polygon, matching how the importer rewinds triangles. Of two same-facing faces in one plane that overlap, the smaller (the later one when equal) is lifted above the larger.
    public static void Separate(IList<Vector3> vertices, IReadOnlyList<int[]> faces)
    {
        var count = faces.Count;
        var normals = new Vector3[count];
        var areas = new float[count];
        var planes = new float[count];
        for (var i = 0; i < count; i++)
        {
            var sum = Vector3.Zero;
            var corners = faces[i];
            for (var c = 0; c < corners.Length; c++)
            {
                var current = vertices[corners[c]];
                var next = vertices[corners[(c + 1) % corners.Length]];
                sum += Vector3.Cross(next, current);
            }

            areas[i] = sum.Length() / 2;
            normals[i] = areas[i] > 0 ? Vector3.Normalize(sum) : Vector3.Zero;
            planes[i] = Vector3.Dot(normals[i], vertices[corners[0]]);
        }

        var order = new List<int>();
        for (var i = 0; i < count; i++)
        {
            if (areas[i] > 0)
                order.Add(i);
        }

        order.Sort((a, b) => areas[a] != areas[b] ? areas[b].CompareTo(areas[a]) : a.CompareTo(b));

        var levels = new int[count];
        for (var position = 0; position < order.Count; position++)
        {
            var face = order[position];
            for (var below = 0; below < position; below++)
            {
                var other = order[below];
                if (Vector3.Dot(normals[face], normals[other]) < SameFacingDot || Math.Abs(planes[face] - planes[other]) > PlaneTolerance)
                    continue;
                if (Overlap(vertices, faces[face], faces[other], normals[face]))
                    levels[face] = Math.Max(levels[face], levels[other] + 1);
            }
        }

        for (var i = 0; i < count; i++)
        {
            if (levels[i] == 0)
                continue;
            var lift = normals[i] * (levels[i] * LiftStep);
            foreach (var corner in faces[i])
                vertices[corner] += lift;
        }
    }

    static bool Overlap(IList<Vector3> vertices, int[] first, int[] second, Vector3 normal)
    {
        var drop = 0;
        if (Math.Abs(normal.Y) > Math.Abs(normal.X))
            drop = 1;
        if (Math.Abs(normal.Z) > Math.Abs(drop == 0 ? normal.X : normal.Y))
            drop = 2;
        for (var a = 1; a < first.Length - 1; a++)
        {
            for (var b = 1; b < second.Length - 1; b++)
            {
                if (TrianglesOverlap(Project(vertices, first[0], first[a], first[a + 1], drop), Project(vertices, second[0], second[b], second[b + 1], drop)))
                    return true;
            }
        }

        return false;
    }

    static Vector2[] Project(IList<Vector3> vertices, int a, int b, int c, int drop)
    {
        return new[] { Flatten(vertices[a], drop), Flatten(vertices[b], drop), Flatten(vertices[c], drop) };
    }

    static Vector2 Flatten(Vector3 point, int drop)
    {
        return drop == 0 ? new Vector2(point.Y, point.Z) : drop == 1 ? new Vector2(point.X, point.Z) : new Vector2(point.X, point.Y);
    }

    // Separating-axis test that counts triangles which only touch along an edge or corner as apart.
    static bool TrianglesOverlap(Vector2[] first, Vector2[] second)
    {
        foreach (var triangle in new[] { first, second })
        {
            for (var edge = 0; edge < 3; edge++)
            {
                var direction = triangle[(edge + 1) % 3] - triangle[edge];
                if (direction.LengthSquared() < OverlapEpsilon * OverlapEpsilon)
                    continue;
                var axis = Vector2.Normalize(new Vector2(-direction.Y, direction.X));
                Range(first, axis, out var firstMin, out var firstMax);
                Range(second, axis, out var secondMin, out var secondMax);
                if (firstMax <= secondMin + OverlapEpsilon || secondMax <= firstMin + OverlapEpsilon)
                    return false;
            }
        }

        return true;
    }

    static void Range(Vector2[] triangle, Vector2 axis, out float min, out float max)
    {
        min = max = Vector2.Dot(triangle[0], axis);
        for (var i = 1; i < 3; i++)
        {
            var projection = Vector2.Dot(triangle[i], axis);
            min = Math.Min(min, projection);
            max = Math.Max(max, projection);
        }
    }
}
