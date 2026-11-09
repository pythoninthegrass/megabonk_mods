using System;

namespace MegabonkLevels;

// Decides when a grind lets go of a rail before the player is launched into the wall at its end.
public static class RailWallEnd
{
    // How far ahead, along the direction of travel, a wall ends the grind. The player is let go as soon as a wall comes inside this range.
    public const float DetachDistance = 5f;

    // A surface counts as a wall only when its normal is this close to horizontal, which keeps floors (normal y 1)
    // and ramp faces (the half pipe passes 45 degrees, normal y 0.71) rideable.
    public const float WallNormalMaxY = 0.3f;

    // The face must also point back at the player, so a rail bar or a wall seen edge on does not end the grind.
    public const float FacingDotMin = 0.7f;

    // Below this horizontal speed the player is not travelling toward anything.
    public const float MinSpeed = 2f;

    // The horizontal speed the player keeps when the grind lets go early. A grind runs at about 19.5, which carries the player
    // through the wall anyway, so the detach caps it: measured on the main half pipe lips against the east wall.
    public const float MaxDismountSpeed = 6f;

    // Upward speed given on the early detach, to take the player off the coping instead of sliding along it. Without it the game
    // catches the same rail again several times before the player comes down.
    public const float DismountHop = 5f;

    // Whether the grind is moving fast enough for a wall ahead to matter.
    public static bool IsMoving(float speed) => speed >= MinSpeed;

    // The horizontal speed to keep when leaving the rail: a grind's own speed is capped, a slower one is left alone.
    public static float DismountSpeed(float speed) => speed <= MaxDismountSpeed ? speed : MaxDismountSpeed;

    // A surface ahead is a wall when it is near vertical (normalY, 0 for a wall, 1 for a floor)
    // and faces the player (againstTravel, the hit normal dotted with the direction back at the player).
    public static bool IsWall(float normalY, float againstTravel) =>
        MathF.Abs(normalY) <= WallNormalMaxY && againstTravel >= FacingDotMin;

    // End the grind when a wall sits within DetachDistance ahead and no other rail is close enough to take it over.
    // wallDistance is the distance to the nearest wall hit, or negative when the way ahead is clear.
    public static bool ShouldDetach(float wallDistance, bool handoffAvailable) =>
        wallDistance >= 0f && wallDistance <= DetachDistance && !handoffAvailable;
}
