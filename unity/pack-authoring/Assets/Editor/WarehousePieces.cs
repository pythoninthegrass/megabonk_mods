using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Numerics;

// Parses the piece tables of docs/thps-warehouse-pieces.md and computes the kit's pivot conventions; free of Unity types so the test project compiles it directly.
public static class WarehousePieces
{
    // One "| piece-..." table row: the asset name, its display name, the literal o groups, the one-based f-line ordinals, and the Module column.
    public sealed class Piece
    {
        public Piece(string id, string name, string[] groups, int[] faces, string module)
        {
            Id = id;
            Name = name;
            Groups = groups;
            Faces = faces;
            Module = module;
        }

        public string Id { get; }
        public string Name { get; }
        public string[] Groups { get; }
        public int[] Faces { get; }
        public string Module { get; }
    }

    public enum PivotRule { RidingTransition, SurfaceCentre, CornerLipIntersection, BottomCentre, LowerFaceCentre }

    // The kit frame of a piece: mesh-space pivot point and the placement yaw about +Y that points local +Z toe toward lip (for riding modules) or 0.
    public readonly struct Placement
    {
        public Placement(Vector3 pivot, float yawDegrees)
        {
            Pivot = pivot;
            YawDegrees = yawDegrees;
        }

        public Vector3 Pivot { get; }
        public float YawDegrees { get; }
    }

    static readonly Dictionary<string, PivotRule> Rules = new Dictionary<string, PivotRule>(StringComparer.Ordinal)
    {
        { "main-transition", PivotRule.RidingTransition },
        { "wall-transition", PivotRule.RidingTransition },
        { "outer-bank", PivotRule.RidingTransition },
        { "bank-end", PivotRule.RidingTransition },
        { "hip", PivotRule.RidingTransition },
        { "hip-apron", PivotRule.RidingTransition },
        { "roll-in", PivotRule.RidingTransition },
        { "kicker", PivotRule.RidingTransition },
        { "convex-tip", PivotRule.RidingTransition },
        { "deck", PivotRule.SurfaceCentre },
        { "flat", PivotRule.SurfaceCentre },
        { "floor", PivotRule.SurfaceCentre },
        { "corner", PivotRule.CornerLipIntersection },
        { "roof", PivotRule.LowerFaceCentre },
        { "prop", PivotRule.BottomCentre },
        { "wall", PivotRule.BottomCentre },
        { "window", PivotRule.BottomCentre },
        { "sign", PivotRule.BottomCentre },
        { "support", PivotRule.BottomCentre },
        { "rail", PivotRule.BottomCentre },
        { "ledge", PivotRule.BottomCentre },
        { "end-cap", PivotRule.BottomCentre },
        { "suppressed-post", PivotRule.BottomCentre },
    };

    // The "| piece-..." rows of the inventory document; every other line (headers, prose, added/retained/settings tables) is skipped.
    public static List<Piece> ParseInventory(string markdown)
    {
        var pieces = new List<Piece>();
        foreach (var line in markdown.Split('\n'))
        {
            if (!line.StartsWith("| piece-", StringComparison.Ordinal))
                continue;
            var cells = line.TrimEnd('\r').Trim().Trim('|').Split('|').Select(cell => cell.Trim()).ToArray();
            if (cells.Length != 5 || cells.Any(string.IsNullOrEmpty))
                throw new FormatException("invalid piece row: " + line);
            pieces.Add(new Piece(cells[0], cells[1], cells[2].Split(',').Select(group => group.Trim()).ToArray(), ParseFaceRanges(cells[3]), cells[4]));
        }

        return pieces;
    }

    // Comma-separated inclusive one-based ranges, "278-280,285-296"; a lone number is a one-face range.
    public static int[] ParseFaceRanges(string text)
    {
        var faces = new List<int>();
        foreach (var token in text.Split(','))
        {
            var parts = token.Trim().Split('-');
            if (parts.Length > 2 || !int.TryParse(parts[0], NumberStyles.None, CultureInfo.InvariantCulture, out var start) || start < 1)
                throw new FormatException("invalid face range: " + token);
            var end = start;
            if (parts.Length == 2 && (!int.TryParse(parts[1], NumberStyles.None, CultureInfo.InvariantCulture, out end) || end < start))
                throw new FormatException("invalid face range: " + token);
            for (var face = start; face <= end; face++)
                faces.Add(face);
        }

        if (faces.Count == 0)
            throw new FormatException("empty face range: " + text);
        return faces.ToArray();
    }

    // Diagnostics for a claimed partition of face ordinals 1..faceCount: unassigned, doubly owned, or out-of-range faces; empty means every face has exactly one owner.
    public static List<string> CoverageErrors(IEnumerable<Piece> pieces, int faceCount)
    {
        var owners = new Dictionary<int, List<string>>();
        foreach (var piece in pieces)
            foreach (var face in piece.Faces)
            {
                if (!owners.TryGetValue(face, out var list))
                    owners[face] = list = new List<string>();
                list.Add(piece.Id);
            }

        var errors = new List<string>();
        for (var face = 1; face <= faceCount; face++)
        {
            if (!owners.TryGetValue(face, out var list))
                errors.Add("unassigned face " + face);
            else if (list.Count > 1)
                errors.Add("face " + face + " assigned more than once (" + string.Join(", ", list) + ")");
        }

        foreach (var face in owners.Keys.Where(face => face < 1 || face > faceCount).OrderBy(face => face))
            errors.Add("unknown face " + face + " (" + string.Join(", ", owners[face]) + ")");
        return errors;
    }

    public static PivotRule RuleFor(string module)
        => Rules.TryGetValue(module, out var rule) ? rule : throw new ArgumentException("no pivot convention for module " + module, nameof(module));

    public static Placement ComputePlacement(PivotRule rule, IReadOnlyList<Vector3> vertices)
    {
        if (vertices.Count == 0)
            throw new ArgumentException("a piece has no vertices", nameof(vertices));
        var minY = vertices.Min(v => v.Y);
        var maxY = vertices.Max(v => v.Y);
        var band = Math.Max(1e-5f, (maxY - minY) * 0.05f);
        switch (rule)
        {
            case PivotRule.RidingTransition:
            {
                var toe = Centroid(vertices.Where(v => v.Y <= minY + band));
                var lip = Centroid(vertices.Where(v => v.Y >= maxY - band));
                var direction = new Vector2(lip.X - toe.X, lip.Z - toe.Z);
                var yaw = direction.LengthSquared() < 1e-12f ? 0f : (float)(Math.Atan2(direction.X, direction.Y) * 180.0 / Math.PI);
                return new Placement(new Vector3(toe.X, minY, toe.Z), yaw);
            }

            case PivotRule.SurfaceCentre:
            {
                var top = Centroid(vertices.Where(v => v.Y >= maxY - band));
                return new Placement(new Vector3(top.X, maxY, top.Z), 0f);
            }

            case PivotRule.CornerLipIntersection:
                return new Placement(CornerPivot(vertices, maxY, band), 0f);

            default:
            {
                var bottom = Centroid(vertices.Where(v => v.Y <= minY + band));
                return new Placement(new Vector3(bottom.X, minY, bottom.Z), 0f);
            }
        }
    }

    // Mesh-space vertices into the piece's stored local space: translated by the pivot, then rotated by -yaw about +Y.
    public static Vector3[] ToLocal(IReadOnlyList<Vector3> vertices, Placement placement)
        => vertices.Select(v => RotateY(v - placement.Pivot, -placement.YawDegrees * MathF.PI / 180f)).ToArray();

    // Inverse of ToLocal, the transform a placement with position = pivot and yaw = YawDegrees applies.
    public static Vector3 ToMeshSpace(Vector3 local, Placement placement)
        => RotateY(local, placement.YawDegrees * MathF.PI / 180f) + placement.Pivot;

    static Vector3 Centroid(IEnumerable<Vector3> points)
    {
        var list = points.ToArray();
        return new Vector3(list.Average(v => v.X), list.Average(v => v.Y), list.Average(v => v.Z));
    }

    static Vector3 RotateY(Vector3 v, float radians)
    {
        var (sin, cos) = (MathF.Sin(radians), MathF.Cos(radians));
        return new Vector3(v.X * cos + v.Z * sin, v.Y, -v.X * sin + v.Z * cos);
    }

    // The corner's deck-height pivot: the two longest edges of the top polygon's convex hull are the straight lip lines; extended, they meet at the corner. Parallel or degenerate lips fall back to the top vertex farthest from the piece's centre.
    static Vector3 CornerPivot(IReadOnlyList<Vector3> vertices, float maxY, float band)
    {
        var top = vertices.Where(v => v.Y >= maxY - band).Select(v => new Vector2(v.X, v.Z)).Distinct().ToArray();
        var centre = new Vector2(vertices.Average(v => v.X), vertices.Average(v => v.Z));
        Vector3 Fallback()
        {
            var far = top.OrderByDescending(p => (p - centre).LengthSquared()).First();
            return new Vector3(far.X, maxY, far.Y);
        }

        var hull = ConvexHull(top);
        if (hull.Count < 3)
            return Fallback();
        var edges = Enumerable.Range(0, hull.Count).Select(i => (A: hull[i], B: hull[(i + 1) % hull.Count]))
            .Where(e => (e.B - e.A).LengthSquared() > 1e-12f)
            .OrderByDescending(e => (e.B - e.A).LengthSquared())
            .ToArray();
        for (var a = 0; a < edges.Length; a++)
            for (var b = a + 1; b < edges.Length; b++)
            {
                var d1 = edges[a].B - edges[a].A;
                var d2 = edges[b].B - edges[b].A;
                var cross = d1.X * d2.Y - d1.Y * d2.X;
                if (MathF.Abs(cross) < 0.1f * d1.Length() * d2.Length())
                    continue;
                var t = ((edges[b].A.X - edges[a].A.X) * d2.Y - (edges[b].A.Y - edges[a].A.Y) * d2.X) / cross;
                var point = edges[a].A + t * d1;
                return new Vector3(point.X, maxY, point.Y);
            }

        return Fallback();
    }

    // Andrew's monotone chain over the XZ plane; returns the hull counter-clockwise.
    static List<Vector2> ConvexHull(Vector2[] points)
    {
        if (points.Length < 3)
            return points.ToList();
        var sorted = points.OrderBy(p => p.X).ThenBy(p => p.Y).ToArray();
        bool TurnsRight(Vector2 o, Vector2 a, Vector2 b) => (a.X - o.X) * (b.Y - o.Y) - (a.Y - o.Y) * (b.X - o.X) <= 0;
        var lower = new List<Vector2>();
        foreach (var p in sorted)
        {
            while (lower.Count >= 2 && TurnsRight(lower[^2], lower[^1], p))
                lower.RemoveAt(lower.Count - 1);
            lower.Add(p);
        }

        var upper = new List<Vector2>();
        foreach (var p in sorted.Reverse())
        {
            while (upper.Count >= 2 && TurnsRight(upper[^2], upper[^1], p))
                upper.RemoveAt(upper.Count - 1);
            upper.Add(p);
        }

        lower.RemoveAt(lower.Count - 1);
        upper.RemoveAt(upper.Count - 1);
        lower.AddRange(upper);
        return lower;
    }
}
