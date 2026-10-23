using System;
using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// Unity-free rules for what the editor's object tools send to the edit stack.
public static class ObjectTools
{
    private const float YawStep = 90f;

    // Grid lines per tile edge, drawn as a visual guide; placement is not snapped to them.
    private const int GridDivisions = 4;
    private const float PositionTolerance = 0.01f;
    private const float DragHoldSeconds = 0.2f;
    private const float LargeRingScale = 0.4f;
    private const float SmallRingScale = 2f;
    private const float SmallRingCap = 3f;

    // Tiles, walls, fill pieces and tile objects (ForestParticles and the like) are scenery, never picked or outlined.
    public static bool IsPickableGenId(string genId) => genId.StartsWith("object:", StringComparison.Ordinal);

    // Disabled renderers (a shrine's charge-radius sphere), particles and the minimap marker are not part of the visible model.
    public static bool IsModelRenderer(string rendererName, bool enabled, bool isParticle) =>
        enabled && !isParticle && rendererName != "MinimapIcon";

    // A model partly buried in the ground has bounds below the surface, which would hide its ring.
    public static float RingBaseY(float boundsMinY, float? surfaceY) =>
        surfaceY is { } surface ? MathF.Max(boundsMinY, surface) : boundsMinY;

    // Large objects such as trees get a ring well inside their canopy bounds; small ones get one just outside the mesh so it is not hidden.
    public static float RingRadius(float extent) =>
        MathF.Max(extent * LargeRingScale, MathF.Min(extent * SmallRingScale, SmallRingCap));

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
    public static float FacingYaw(float cameraYaw) => NormalizeYaw(MathF.Round((cameraYaw + 180f) / YawStep) * YawStep);

    public static EditOp Place(CatalogId catalogId, Vector3Data position, Vector3Data prefabRotation, Vector3Data scale, float cameraYaw) =>
        new PlaceObject(catalogId.Serialize(), position, prefabRotation with { Y = FacingYaw(cameraYaw) }, scale).ToEditOp();

    public static EditOp Move(ObjectTarget target, TransformData current, Vector3Data position) =>
        new MoveObject(target, current with { Position = position }).ToEditOp();

    public static EditOp Rotate(ObjectTarget target, TransformData current, bool clockwise)
    {
        var yaw = NormalizeYaw(current.Rotation.Y + (clockwise ? YawStep : -YawStep));
        return new MoveObject(target, current with { Rotation = current.Rotation with { Y = yaw } }).ToEditOp();
    }

    public static EditOp Remove(ObjectTarget target) => new RemoveObject(target).ToEditOp();

    private static float NormalizeYaw(float yaw)
    {
        var wrapped = yaw % 360f;
        return wrapped < 0f ? wrapped + 360f : wrapped;
    }
}
