using System;

namespace MegabonkLevels;

// Unity-free rules for what the editor's object tools send to the edit stack.
public static class ObjectTools
{
    private const float YawStep = 90f;

    // The cell's centre at its tile surface; a ramp's surface is half a level above its base.
    public static Vector3Data SnapPosition(int x, int z, TileState state, int width, int depth, float spacing, float tileHeight)
    {
        var (centreX, centreZ) = PositionReadout.CellCentre(x, z, width, depth, spacing);
        var rampLift = state.Slope == SlopeDirection.None ? 0f : tileHeight / 2f;
        return new Vector3Data(centreX, state.Height * tileHeight + rampLift, centreZ);
    }

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
