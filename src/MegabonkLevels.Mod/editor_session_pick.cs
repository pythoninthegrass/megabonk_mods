using System.Collections.Generic;

namespace MegabonkLevels;

// Keeps live-playtest history until a different run replaces the edited level.
public static class EditorSessionPick
{
    // Returns true when a new session replaces the current one.
    public static bool Pick(
        int currentGeneration,
        EditorEditSession currentSession,
        int currentRunGeneration,
        int currentLastSavedEditCount,
        IReadOnlyList<EditOp> seedEdits,
        out EditorEditSession session,
        out int runGeneration,
        out int lastSavedEditCount)
    {
        if (currentSession == null || currentRunGeneration != currentGeneration)
        {
            session = new EditorEditSession(seedEdits);
            runGeneration = currentGeneration;
            lastSavedEditCount = seedEdits.Count;
            return true;
        }

        session = currentSession;
        runGeneration = currentRunGeneration;
        lastSavedEditCount = currentLastSavedEditCount;
        return false;
    }
}
