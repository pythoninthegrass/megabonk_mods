namespace MegabonkLevels;

public static class EditorReenterPolicy
{
    public static bool ShouldEnter(bool requested, bool active, bool runInProgress, bool consoleOpen) =>
        requested && !active && runInProgress && !consoleOpen;
}
