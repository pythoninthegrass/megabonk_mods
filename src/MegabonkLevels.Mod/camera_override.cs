using Il2Cpp;
using UnityEngine;

namespace MegabonkLevels;

// Re-applies a requested camera pose after the game's own PlayerCamera update; driven from MelonMod.OnLateUpdate.
// The game never rewrites the camera's own transform, so Clear restores the pose saved before the first override.
public static class CameraOverride
{
    private static CameraPose? _pose;
    private static bool _hasSaved;
    private static Vector3 _savedLocalPosition;
    private static Quaternion _savedLocalRotation;

    public static void Set(CameraPose pose) => _pose = pose;

    public static void Clear()
    {
        _pose = null;
        if (!_hasSaved)
        {
            return;
        }

        _hasSaved = false;
        var camera = PlayerCamera.Instance?.camera;
        if (camera != null)
        {
            camera.transform.localPosition = _savedLocalPosition;
            camera.transform.localRotation = _savedLocalRotation;
        }
    }

    public static void Apply()
    {
        if (_pose is not { } pose)
        {
            return;
        }

        var camera = PlayerCamera.Instance?.camera;
        if (camera == null)
        {
            return;
        }

        var transform = camera.transform;
        if (!_hasSaved)
        {
            _savedLocalPosition = transform.localPosition;
            _savedLocalRotation = transform.localRotation;
            _hasSaved = true;
        }

        transform.position = new Vector3(pose.X, pose.Y, pose.Z);
        transform.rotation = Quaternion.Euler(pose.Rx, pose.Ry, pose.Rz);
    }
}
