namespace MegabonkLevels;

// Widens the catch on a level that gates grinding, so holding the slide button is enough to get onto a rail. The game's own
// catch needs the player's collider to touch the rail's, and a rail's collider stops short of its own spline ends, so a grind
// started only on a dead-centre approach. This looks for a rail within a radius instead, the way RailHandoff looks for one to
// chain onto, and only while the button is held, which is the player asking for it.
public static class GrindAssist
{
    // How far from the player's feet a rail may be and still be caught. The game needs contact; this is the slack.
    public const float CatchRadius = 2f;

    // A bar this far above the feet is one the player is passing under, so it is left alone. A coping bar sits at the feet
    // or just below them, which is where a grind begins.
    public const float CatchRiseAboveFeet = 1f;

    // Whether to look for a rail to put the player on: only where the gate is in force, only while the button is held, and
    // only when they are not already on a rail.
    public static bool Assists(bool customLevelActive, bool levelOptsIn, bool slideHeld, bool grinding) =>
        !grinding && GrindGate.UsesGate(customLevelActive, levelOptsIn) && slideHeld;

    // Whether a bar at railY is at a height to be caught from, given the player's feet are at feetY.
    public static bool WithinBand(float railY, float feetY) => railY - feetY <= CatchRiseAboveFeet;
}
