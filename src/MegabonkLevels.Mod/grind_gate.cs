namespace MegabonkLevels;

// Decides whether a rail touch starts a grind. The game starts one on contact; a level that sets grindRequiresSlide
// asks for the slide button first, so a player riding over a coping rail, or ollieing off a lip, keeps their momentum.
public static class GrindGate
{
    // The game's Rewired action for the slide button (stringliteral.json holds "Slide").
    public const string SlideAction = "Slide";

    // A failed input read reports the button held, so an unreachable Rewired leaves the game's own behaviour
    // (grind on contact) rather than making grinding impossible.
    public const bool SlideHeldWhenReadFails = true;

    // Whether this run gates grind starts at all: a mod-loaded level that asked for it.
    public static bool UsesGate(bool customLevelActive, bool levelOptsIn) => customLevelActive && levelOptsIn;

    // Whether a rail touch may start a grind: anywhere the gate is not in force, or while the slide button is held.
    // The same rule decides a handoff onto the next rail, so a released button ends the chain at a joint.
    public static bool AllowsStart(bool customLevelActive, bool levelOptsIn, bool slideHeld) =>
        !UsesGate(customLevelActive, levelOptsIn) || slideHeld;
}
