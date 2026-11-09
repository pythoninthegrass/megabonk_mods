using System;
using System.Collections.Generic;

namespace MegabonkLevels;

public readonly record struct Vec3(float X, float Y, float Z);

// The boss portal hangs in the Warehouse's glass box and the bosses it summons come out with it: the game drops them
// inside or onto the box and they climb its walls. Instead of an authored anchor, the redirect teleports every boss
// the portal summons to a random walkable spot in the level's interior at least MinDistanceFromSpawner away from the
// box, so a curse copy cannot land beside the shrine it came from.
public static class BossSpawnRedirect
{
    // Frames the arming stays alive: the spawner calls EnemyManager.SpawnBoss from its own Interact, so the call lands
    // on this frame or the next, and a window this short cannot catch an unrelated spawn.
    public const int ArmWindowFrames = 2;
    // A boss has to land this far from the portal's own position, which is inside the hanging glass box.
    public const float MinDistanceFromSpawner = 35f;
    // ...and no further, so it stays inside the level's interior rather than on some far tile.
    public const float MaxDistanceFromSpawner = 68f;
    // Curse copies spawn apart, never sharing a spot.
    public const float MinSpacingBetweenCopies = 20f;
    // A surface this close above the kill floor is where the level kills things; bosses must not stand there.
    public const float KillFloorMargin = 5f;

    // The glass box spans the floor and roof around the portal; a miniboss spawning in this band around it is stuck.
    public const float BoxFloorBelowSpawner = 2f;
    public const float BoxRoofAboveSpawner = 10f;

    // A from-scratch level places its own boss spawner, so it only gets the redirect when its file asks for it.
    public static bool ShouldArm(bool customLevelActive, bool fromScratch, bool redirectRequested) => customLevelActive && (!fromScratch || redirectRequested);

    // True when a spawn at pos sits within the glass box's footprint and height band around the portal.
    public static bool IsInsideBossBox(Vec3 pos, Vec3 spawner) =>
        XzDistance(pos, spawner) < MinDistanceFromSpawner &&
        pos.Y >= spawner.Y - BoxFloorBelowSpawner &&
        pos.Y <= spawner.Y + BoxRoofAboveSpawner;

    public static int ExpectedMoves(int bossCurses) => Math.Max(1, 1 + bossCurses);

    public static bool ShouldConsume(int? armedFrame, int frame, int windowFrames = ArmWindowFrames) =>
        armedFrame.HasValue && frame >= armedFrame.Value && frame <= armedFrame.Value + windowFrames;

    // True when the arming should be cleared: either the count is met or the window has passed.
    public static bool ShouldExpire(int? armedFrame, int expectedMoves, int moveCount, int frame, int windowFrames = ArmWindowFrames) =>
        armedFrame.HasValue && (moveCount >= expectedMoves || frame > armedFrame.Value + windowFrames);

    // Deterministic ring samples around the spawner, inside the distance band; the patch raycasts each and picks the
    // best of the whole ring with PickSpot, not the first that passes.
    public static List<Vec3> CandidateRing(Vec3 spawner, int seed, int count)
    {
        var random = new Random(seed);
        var candidates = new List<Vec3>(count);
        for (var i = 0; i < count; i++)
        {
            var angle = (float)(random.NextDouble() * 2.0 * Math.PI);
            var distance = MinDistanceFromSpawner + (float)(random.NextDouble() * (MaxDistanceFromSpawner - MinDistanceFromSpawner));
            candidates.Add(new Vec3(spawner.X + MathF.Cos(angle) * distance, spawner.Y, spawner.Z + MathF.Sin(angle) * distance));
        }

        return candidates;
    }

    public static bool SpotUsable(Vec3 floorPoint, Vec3 spawner, float killFloorY, IReadOnlyList<Vec3> taken)
    {
        if (XzDistance(floorPoint, spawner) < MinDistanceFromSpawner)
        {
            return false;
        }

        if (floorPoint.Y < killFloorY + KillFloorMargin)
        {
            return false;
        }

        foreach (var other in taken)
        {
            if (XzDistance(floorPoint, other) < MinSpacingBetweenCopies) return false;
        }

        return true;
    }

    // Best-of-ring selection: the usable spot whose nearest already-placed copy is farthest away (XZ). See the
    // "Boss spawn redirect" section in docs/development.md.
    public static bool PickSpot(IReadOnlyList<Vec3> usable, IReadOnlyList<Vec3> taken, out Vec3 spot) =>
        Maximin.Pick(usable, taken, XzDistance, out spot);

    // The game lifts a spawned enemy above the position it was asked for, so the offset it applied is kept and the
    // boss's feet, not its pivot, land on the floor.
    public static Vec3 FloorPlacement(Vec3 floorPoint, Vec3 requestedPosition, Vec3 actualPosition) =>
        new(floorPoint.X, floorPoint.Y + actualPosition.Y - requestedPosition.Y, floorPoint.Z);

    public static float XzDistance(Vec3 a, Vec3 b)
    {
        var dx = a.X - b.X;
        var dz = a.Z - b.Z;
        return MathF.Sqrt(dx * dx + dz * dz);
    }
}
