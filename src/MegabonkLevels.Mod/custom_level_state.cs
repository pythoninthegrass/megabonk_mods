namespace MegabonkLevels;

// Whether the currently active run was started via LevelLoaderPatch (TASK-004.01) rather than the
// game's own menu flow. MapController.StartNewMap is the single entry point both paths funnel through
// (confirmed live by TASK-004.01's SceneTransitionProbe), so OnRunStarting() is driven from a Harmony
// prefix on that method and resolves whatever LoadAndStart most recently marked pending into IsActive —
// one source of truth, so a normal run always re-resolves to inactive even right after a custom one.
public static class CustomLevelState
{
    public static bool IsActive { get; private set; }

    private static bool _pendingStart;

    // Set by LevelLoaderPatch immediately before it calls MapController.StartNewMap.
    public static void MarkPendingStart()
    {
        _pendingStart = true;
    }

    // Called from the StartNewMap Harmony prefix for every run, modded or not.
    public static void OnRunStarting()
    {
        IsActive = _pendingStart;
        _pendingStart = false;
    }

    public static void Reset()
    {
        IsActive = false;
        _pendingStart = false;
    }
}
