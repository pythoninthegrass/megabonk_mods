namespace MegabonkLevels;

// Custom-loaded or editor-used runs cannot submit scores, achievements or stats.
// Starting a new normal run clears the guard; leaving the editor does not.
public static class CustomLevelState
{
    public static bool IsActive { get; private set; }

    private static bool _pendingStart;

    public static void MarkEditorUsed() => IsActive = true;

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
