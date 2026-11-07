namespace MegabonkLevels;

// Unity-free rules for the Place tool's cursor preview: when the ghost stands and which rotation it carries.
public static class PlacePreview
{
    // The ghost marks where a click would put the object, so it needs what that click needs.
    public static bool IsVisible(bool placeTool, bool pointerBlocked, bool hasSelection, bool hasPrefab, bool hasCamera, bool hasPosition) =>
        placeTool && !pointerBlocked && hasSelection && hasPrefab && hasCamera && hasPosition;

    // Faces the camera until R/F/G steps it; after that the rotation is the user's and the camera no longer steers it.
    public static Vector3Data Rotation(Vector3Data? userRotation, Vector3Data prefabRotation, float cameraYaw, RotationAxis? axis, bool positive) =>
        axis is { } pressed
            ? ObjectTools.StepRotation(userRotation ?? Facing(prefabRotation, cameraYaw), pressed, positive)
            : userRotation ?? Facing(prefabRotation, cameraYaw);

    public static Vector3Data Facing(Vector3Data prefabRotation, float cameraYaw) => prefabRotation with { Y = ObjectTools.FacingYaw(cameraYaw) };
}
