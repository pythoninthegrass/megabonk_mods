namespace MegabonkLevels;

// Preserves the editor's undo/redo session across a playtest reload (TASK-005.06). The editor UI
// lives in a Unity-heavy class; this stays Unity-free so the round-trip is unit tested.
public sealed class PlaytestCoordinator
{
    private EditorEditSession _session;
    private int _lastSavedEditCount;
    private bool _active;

    public bool Active => _active;

    // Captures the session the editor should keep when a playtest begins.
    public void Begin(EditorEditSession session, int lastSavedEditCount)
    {
        _session = session;
        _lastSavedEditCount = lastSavedEditCount;
        _active = true;
    }

    // Returns the preserved session when returning from a playtest, clearing the coordinator.
    // Returns false when there is nothing to restore (no playtest, or a failed start discarded it).
    public bool TryRestore(out EditorEditSession session, out int lastSavedEditCount)
    {
        if (!_active || _session == null)
        {
            session = null;
            lastSavedEditCount = 0;
            return false;
        }

        session = _session;
        lastSavedEditCount = _lastSavedEditCount;
        _active = false;
        return true;
    }

    // Called when a playtest start fails, so the editor keeps its live session for a retry.
    public void Discard()
    {
        _session = null;
        _active = false;
    }
}
