using System.Collections.Generic;

namespace MegabonkLevels;

// Decides which undo/redo session to install when entering editor mode (TASK-005.06). Unity-free so
// the restore-vs-reset choice is unit tested without the editor UI.
public static class EditorSessionPick
{
    // Returns true when the caller should install the returned values, false when the current
    // session should be kept unchanged. A preserved playtest session wins; otherwise the session
    // is reset when there is none yet or the run generation changed.
    public static bool Pick(
        PlaytestCoordinator playtest,
        int currentGeneration,
        EditorEditSession currentSession,
        int currentRunGeneration,
        IReadOnlyList<EditOp> seedEdits,
        out EditorEditSession session,
        out int runGeneration,
        out int lastSavedEditCount)
    {
        if (playtest != null && playtest.TryRestore(out var restored, out var saved))
        {
            session = restored;
            runGeneration = currentGeneration;
            lastSavedEditCount = saved;
            return true;
        }

        if (currentSession == null || currentRunGeneration != currentGeneration)
        {
            session = new EditorEditSession(seedEdits);
            runGeneration = currentGeneration;
            lastSavedEditCount = seedEdits.Count;
            return true;
        }

        session = currentSession;
        runGeneration = currentRunGeneration;
        lastSavedEditCount = 0;
        return false;
    }
}
