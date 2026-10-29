using System;
using System.Collections.Generic;

namespace MegabonkLevels;

public readonly record struct Vec3(float X, float Y, float Z);

// The boss portal hangs in the Warehouse's glass box and the boss it summons comes out on the ground. The portal is a
// game object with its own collider, so it is hidden and the level authors where the boss appears instead.
public static class BossSpawnRedirect
{
    // Frames the arming stays alive: the spawner calls EnemyManager.SpawnBoss from its own Interact, so the call lands
    // on this frame or the next, and a window this short cannot catch an unrelated spawn.
    public const int ArmWindowFrames = 2;

    public static bool IsUsablePosition(IReadOnlyList<float> position) =>
        position is { Count: 3 }
        && float.IsFinite(position[0])
        && float.IsFinite(position[1])
        && float.IsFinite(position[2]);

    public static bool ShouldArm(bool customLevelActive, IReadOnlyList<float> position) =>
        customLevelActive && IsUsablePosition(position);

    public static bool ShouldConsume(int? armedFrame, int frame, int windowFrames = ArmWindowFrames) =>
        armedFrame.HasValue && frame >= armedFrame.Value && frame <= armedFrame.Value + windowFrames;

    // The game lifts a spawned enemy above the position it was asked for, so the offset it applied is kept and only the
    // requested point moves: that puts the boss's feet, not its pivot, on the authored ground.
    public static Vec3 Placement(Vec3 anchor, Vec3 requestedPosition, Vec3 actualPosition) =>
        new(anchor.X + actualPosition.X - requestedPosition.X,
            anchor.Y + actualPosition.Y - requestedPosition.Y,
            anchor.Z + actualPosition.Z - requestedPosition.Z);
}
