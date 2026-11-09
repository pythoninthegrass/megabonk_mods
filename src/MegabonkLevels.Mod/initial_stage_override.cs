namespace MegabonkLevels;

public sealed class InitialStageOverride
{
    private int? _pending;

    public void Arm(int stageIndex, bool development, bool enabled)
    {
        _pending = development && enabled ? stageIndex : null;
    }

    public int? TakeBeforeAdvance(int currentIndex)
    {
        var requested = _pending;
        _pending = null;
        return currentIndex == -1 ? requested - 1 : null;
    }
}
