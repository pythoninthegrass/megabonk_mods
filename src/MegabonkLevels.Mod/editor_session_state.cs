namespace MegabonkLevels;

// Records what entering editor mode changed so leaving restores exactly that.
public sealed class EditorSessionState
{
    private bool _gamePausedBefore;

    public bool Active { get; private set; }

    public bool Enter(bool gamePausedBefore)
    {
        if (Active)
        {
            return false;
        }

        Active = true;
        _gamePausedBefore = gamePausedBefore;
        return true;
    }

    // A game that was already paused on entry (a level-up dialog, say) must stay paused on exit.
    public bool TryExit(out bool shouldUnpause)
    {
        shouldUnpause = false;
        if (!Active)
        {
            return false;
        }

        Active = false;
        shouldUnpause = !_gamePausedBefore;
        return true;
    }
}
