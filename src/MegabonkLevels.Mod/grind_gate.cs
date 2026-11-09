namespace MegabonkLevels;

// Decides whether the slide button is being held, which is what grinding means on a level that asks for it. The game
// starts a grind on contact and stays on the rail by itself; here the button gates all of it, so a player riding over a
// coping rail, or ollieing off a lip, keeps their momentum, and one who lets go comes off the rail.
public static class GrindGate
{
    // The game's Rewired action for the slide button (stringliteral.json holds "Slide").
    public const string SlideAction = "Slide";

    // A failed input read reports the button held, so an unreachable Rewired leaves the game's own behaviour (grind on
    // contact, stay on the rail) rather than making grinding impossible or throwing the player off mid-grind.
    public const bool SlideHeldWhenReadFails = true;

    // Whether this run gates grinding at all: a mod-loaded level that asked for the slide button.
    public static bool UsesGate(bool customLevelActive, bool levelOptsIn) => customLevelActive && levelOptsIn;

    // The one rule, asked in three places: may a rail touch start a grind, may a joint carry it onto the next rail, and
    // may it keep running at all. Anywhere the gate is not in force the game does as it likes; on an opted-in level the
    // answer is the button, so letting go ends the grind instead of leaving the player riding to the next junction.
    public static bool AllowsGrind(bool customLevelActive, bool levelOptsIn, bool slideHeld) =>
        !UsesGate(customLevelActive, levelOptsIn) || slideHeld;
}
