using System;

namespace MegabonkLevels;

// Per-frame input for the free-fly camera: movement axes in [-1, 1], raw mouse axis units.
public readonly record struct FreeFlyInput(float Forward = 0f, float Right = 0f, float Up = 0f, float MouseDx = 0f, float MouseDy = 0f, bool Fast = false);

public readonly record struct FreeFlySettings(float MoveSpeed, float FastMultiplier, float LookDegreesPerUnit);

// Pure free-fly camera maths on the same pose type CameraOverride consumes (Rx = pitch, Ry = yaw, degrees).
public static class FreeFlyCamera
{
    private const float MaxPitchDegrees = 89f;
    private const float DegreesToRadians = MathF.PI / 180f;

    public const float OverviewPitchDegrees = 40f;
    private const float OverviewHeight = 60f;

    // A zoomed-out view from +Z looking down at the target, so +X runs to the screen's left; the target stays centred.
    public static CameraPose OverviewPose(float targetX, float targetY, float targetZ)
    {
        var back = OverviewHeight / MathF.Tan(OverviewPitchDegrees * DegreesToRadians);
        return new CameraPose(targetX, targetY + OverviewHeight, targetZ + back, OverviewPitchDegrees, 180f, 0f);
    }

    public static CameraPose Step(CameraPose pose, FreeFlyInput input, float deltaSeconds, FreeFlySettings settings)
    {
        var pitch = Math.Clamp(pose.Rx - input.MouseDy * settings.LookDegreesPerUnit, -MaxPitchDegrees, MaxPitchDegrees);
        var yaw = WrapDegrees(pose.Ry + input.MouseDx * settings.LookDegreesPerUnit);

        var pitchRadians = pitch * DegreesToRadians;
        var yawRadians = yaw * DegreesToRadians;
        var (sinYaw, cosYaw) = MathF.SinCos(yawRadians);
        var (sinPitch, cosPitch) = MathF.SinCos(pitchRadians);

        var forward = (X: cosPitch * sinYaw, Y: -sinPitch, Z: cosPitch * cosYaw);
        var right = (X: cosYaw, Y: 0f, Z: -sinYaw);

        var dx = forward.X * input.Forward + right.X * input.Right;
        var dy = forward.Y * input.Forward + input.Up;
        var dz = forward.Z * input.Forward + right.Z * input.Right;

        var length = MathF.Sqrt(dx * dx + dy * dy + dz * dz);
        if (length > 1f)
        {
            dx /= length;
            dy /= length;
            dz /= length;
        }

        var speed = settings.MoveSpeed * (input.Fast ? settings.FastMultiplier : 1f) * deltaSeconds;
        return pose with
        {
            X = pose.X + dx * speed,
            Y = pose.Y + dy * speed,
            Z = pose.Z + dz * speed,
            Rx = pitch,
            Ry = yaw,
        };
    }

    private static float WrapDegrees(float degrees)
    {
        var wrapped = degrees % 360f;
        return wrapped < 0f ? wrapped + 360f : wrapped;
    }
}
