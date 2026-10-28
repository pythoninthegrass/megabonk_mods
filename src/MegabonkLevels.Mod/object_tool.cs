using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

public enum RotationAxis
{
    Pitch,
    Yaw,
    Roll,
}

// Unity-free rules for what the editor's object tools send to the edit stack.
public static class ObjectTools
{
    private const float QuarterTurn = 90f;

    // Grid lines per tile edge, drawn as a visual guide; placement is not snapped to them.
    private const int GridDivisions = 4;
    private const float GimbalLimit = 0.99999f;
    private const float PositionTolerance = 0.01f;
    private const float FloatingLift = 2f;
    public const float SnapDistance = 2f;
    private const float UnitsPerPixel = 0.05f;
    private const float DragHoldSeconds = 0.2f;
    private const float FootprintClearance = 1.1f;
    private const float MinRingRadius = 0.5f;

    // Tiles, walls, fill pieces and tile objects (ForestParticles and the like) are scenery, never picked or outlined.
    public static bool IsPickableGenId(string genId) => genId.StartsWith("object:", StringComparison.Ordinal);

    // Disabled renderers (a shrine's charge-radius sphere), particles and the minimap marker are not part of the visible model.
    public static bool IsModelRenderer(string rendererName, bool enabled, bool isParticle) =>
        enabled && !isParticle && rendererName != "MinimapIcon";

    // A model partly buried in the ground has bounds below the surface, which would hide its ring.
    public static float RingBaseY(float boundsMinY, float? surfaceY) =>
        surfaceY is { } surface ? MathF.Max(boundsMinY, surface) : boundsMinY;

    // The ring sits on the physical ground under the object, but an intentionally elevated object (its origin above
    // the ground) keeps its own base instead of dropping to the terrain.
    public static float RingBaseY(float? groundY, float boundsMinY, float originY, float? surfaceY)
    {
        var ownBase = MathF.Min(boundsMinY, originY);
        if (groundY is { } ground)
        {
            return MathF.Max(ground, ownBase);
        }

        return RingBaseY(boundsMinY, surfaceY);
    }

    // Of the ground heights the probe found, the object rests on the one nearest its own origin, so overhanging
    // geometry above a chest cannot lift its ring off the floor.
    public static float? SupportY(float[] hitYs, float originY)
    {
        if (hitYs.Length == 0)
        {
            return null;
        }

        var best = hitYs[0];
        var bestDistance = MathF.Abs(best - originY);
        for (var i = 1; i < hitYs.Length; i++)
        {
            var distance = MathF.Abs(hitYs[i] - originY);
            if (distance < bestDistance)
            {
                best = hitYs[i];
                bestDistance = distance;
            }
        }

        return best;
    }

    // Enclosing circle of the base footprint with modest clearance, so the ring hugs the object at its base.
    public static float RingRadius(float extentX, float extentZ) =>
        MathF.Max(MinRingRadius, MathF.Sqrt(extentX * extentX + extentZ * extentZ) * FootprintClearance);

    // Evenly spaced points on a horizontal circle, starting on the +X axis; drawn as a closed loop.
    public static IReadOnlyList<Vector3Data> Ring(float centreX, float y, float centreZ, float radius, int segments)
    {
        var points = new Vector3Data[segments];
        for (var i = 0; i < segments; i++)
        {
            var angle = 2f * MathF.PI * i / segments;
            points[i] = new Vector3Data(centreX + radius * MathF.Cos(angle), y, centreZ + radius * MathF.Sin(angle));
        }

        return points;
    }

    // An object resting on the surface keeps its lift over the surface it is dragged across; a floating one keeps its own height and only settles onto a surface within snap range.
    public static float DragY(float tileSurfaceY, float lift, float floatingY, IReadOnlyList<float> nearbySurfaceYs)
    {
        if (lift <= FloatingLift)
        {
            return tileSurfaceY + lift;
        }

        var surfaces = new List<float>(nearbySurfaceYs) { tileSurfaceY };
        return SnapY(floatingY, surfaces);
    }

    // The nearest surface within snap range, otherwise the height unchanged.
    public static float SnapY(float y, IReadOnlyList<float> surfaceYs)
    {
        var best = y;
        var bestDistance = SnapDistance;
        for (var i = 0; i < surfaceYs.Count; i++)
        {
            var distance = MathF.Abs(surfaceYs[i] - y);
            if (distance <= bestDistance)
            {
                best = surfaceYs[i];
                bestDistance = distance;
            }
        }

        return best;
    }

    public static float RaiseBy(float y, float mouseDeltaPixels) => y + mouseDeltaPixels * UnitsPerPixel;

    // The cursor point kept inside its cell, at the tile surface there.
    public static Vector3Data PositionAt(int x, int z, TileState state, int width, int depth, float spacing, float tileHeight, float pointX, float pointZ)
    {
        var (centreX, centreZ) = PositionReadout.CellCentre(x, z, width, depth, spacing);
        var half = spacing / 2f;
        var offsetX = Math.Clamp(pointX - centreX, -half, half);
        var offsetZ = Math.Clamp(pointZ - centreZ, -half, half);
        return new Vector3Data(centreX + offsetX, SurfaceY(state, offsetX, offsetZ, spacing, tileHeight), centreZ + offsetZ);
    }

    // The tile surface at an offset from the cell centre; a ramp rises a full level from its downhill edge to its uphill edge.
    public static float SurfaceY(TileState state, float offsetX, float offsetZ, float spacing, float tileHeight)
    {
        var baseY = state.Height * tileHeight;
        if (state.Slope == SlopeDirection.None)
        {
            return baseY;
        }

        var (dx, dz) = TilePlacement.UphillVector(state.Slope);
        return baseY + tileHeight * (0.5f + (offsetX * dx + offsetZ * dz) / spacing);
    }

    // A single path over the cell's quarter-tile grid lines; every connecting segment runs along the cell edge.
    public static IReadOnlyList<Vector3Data> GridLines(int x, int z, TileState state, int width, int depth, float spacing, float tileHeight, float lift)
    {
        var (centreX, centreZ) = PositionReadout.CellCentre(x, z, width, depth, spacing);
        var half = spacing / 2f;
        var step = spacing / GridDivisions;
        var points = new List<Vector3Data>();

        Vector3Data At(float offsetX, float offsetZ) =>
            new(centreX + offsetX, SurfaceY(state, offsetX, offsetZ, spacing, tileHeight) + lift, centreZ + offsetZ);

        for (var i = 0; i <= GridDivisions; i++)
        {
            var offsetX = -half + i * step;
            points.Add(At(offsetX, i % 2 == 0 ? -half : half));
            points.Add(At(offsetX, i % 2 == 0 ? half : -half));
        }

        for (var j = GridDivisions; j >= 0; j--)
        {
            var offsetZ = -half + j * step;
            var fromEast = (GridDivisions - j) % 2 == 0;
            points.Add(At(fromEast ? half : -half, offsetZ));
            points.Add(At(fromEast ? -half : half, offsetZ));
        }

        return points;
    }

    // True when an object of the same prefab already stands at the position.
    public static bool IsStacked(string prefabName, Vector3Data position, IEnumerable<(string PrefabName, Vector3Data Position)> others) =>
        others.Any(o => o.PrefabName == prefabName && !HasMoved(o.Position, position));

    // A press only turns into a drag once held this long, so a quick click selects without moving.
    public static bool DragStarted(float heldSeconds) => heldSeconds >= DragHoldSeconds;

    public static bool HasMoved(Vector3Data from, Vector3Data to) =>
        MathF.Abs(from.X - to.X) > PositionTolerance || MathF.Abs(from.Y - to.Y) > PositionTolerance || MathF.Abs(from.Z - to.Z) > PositionTolerance;

    // Faces the camera: the opposite of its yaw, rounded to a quarter turn.
    public static float FacingYaw(float cameraYaw) => NormalizeAngle(MathF.Round((cameraYaw + 180f) / QuarterTurn) * QuarterTurn);

    public static EditOp Place(CatalogId catalogId, Vector3Data position, Vector3Data prefabRotation, Vector3Data scale, float cameraYaw) =>
        new PlaceObject(catalogId.Serialize(), position, prefabRotation with { Y = FacingYaw(cameraYaw) }, scale).ToEditOp();

    public static EditOp Move(ObjectTarget target, TransformData current, Vector3Data position) =>
        new MoveObject(target, current with { Position = position }).ToEditOp();

    // Steps the object a quarter turn about a world axis; yaw edits the Y euler directly, pitch and roll compose in world space.
    public static EditOp Rotate(ObjectTarget target, TransformData current, RotationAxis axis, bool positive)
    {
        var rotation = axis == RotationAxis.Yaw
            ? current.Rotation with { Y = NormalizeAngle(current.Rotation.Y + (positive ? QuarterTurn : -QuarterTurn)) }
            : WorldStep(current.Rotation, axis, positive ? QuarterTurn : -QuarterTurn);
        return new MoveObject(target, current with { Rotation = rotation }).ToEditOp();
    }

    public static EditOp Remove(ObjectTarget target) => new RemoveObject(target).ToEditOp();

    // Rotation is Unity's euler order: Z first, then X, then Y, all about world axes (matrix Ry * Rx * Rz).
    private static Vector3Data WorldStep(Vector3Data euler, RotationAxis axis, float degrees)
    {
        var m = Multiply(AxisMatrix(axis, degrees), EulerMatrix(euler));
        var sinX = -m[1, 2];
        if (MathF.Abs(sinX) < GimbalLimit)
        {
            return Snap(RadToDeg(MathF.Asin(sinX)), RadToDeg(MathF.Atan2(m[0, 2], m[2, 2])), RadToDeg(MathF.Atan2(m[1, 0], m[1, 1])));
        }

        return Snap(sinX > 0f ? 90f : -90f, RadToDeg(MathF.Atan2(-m[2, 0], m[0, 0])), 0f);
    }

    private static float[,] EulerMatrix(Vector3Data euler) =>
        Multiply(Multiply(AxisMatrix(RotationAxis.Yaw, euler.Y), AxisMatrix(RotationAxis.Pitch, euler.X)), AxisMatrix(RotationAxis.Roll, euler.Z));

    private static float[,] AxisMatrix(RotationAxis axis, float degrees)
    {
        var radians = degrees * MathF.PI / 180f;
        var (s, c) = (MathF.Sin(radians), MathF.Cos(radians));
        return axis switch
        {
            RotationAxis.Pitch => new float[,] { { 1, 0, 0 }, { 0, c, -s }, { 0, s, c } },
            RotationAxis.Yaw => new float[,] { { c, 0, s }, { 0, 1, 0 }, { -s, 0, c } },
            _ => new float[,] { { c, -s, 0 }, { s, c, 0 }, { 0, 0, 1 } },
        };
    }

    private static float[,] Multiply(float[,] a, float[,] b)
    {
        var result = new float[3, 3];
        for (var row = 0; row < 3; row++)
        {
            for (var col = 0; col < 3; col++)
            {
                result[row, col] = a[row, 0] * b[0, col] + a[row, 1] * b[1, col] + a[row, 2] * b[2, col];
            }
        }

        return result;
    }

    private static float RadToDeg(float radians) => radians * 180f / MathF.PI;

    // Rounds away float noise so a quarter-turn lands on exact degrees, then wraps into 0 to 360.
    private static Vector3Data Snap(float x, float y, float z) =>
        new(NormalizeAngle(MathF.Round(x, 3)), NormalizeAngle(MathF.Round(y, 3)), NormalizeAngle(MathF.Round(z, 3)));

    private static float NormalizeAngle(float angle)
    {
        var wrapped = angle % 360f;
        return wrapped < 0f ? wrapped + 360f : wrapped + 0f;
    }
}
