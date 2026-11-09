namespace MegabonkLevels;

public enum EditorLoadAction
{
    InPlace,
    FreshRun,
    Refuse,
}

// Authored starts need the startup placement lifecycle; from-scratch grids also need a fresh run.
public static class EditorLoadPlan
{
    public static EditorLoadAction Decide(LevelFile? current, LevelFile target)
    {
        if (target.PlayerStart != null || target.IsFromScratch || current is { IsFromScratch: true })
        {
            return EditorLoadAction.FreshRun;
        }

        if (current is { } live
            && (live.Map != target.Map || live.StageIndex != target.StageIndex || live.Seed != target.Seed || live.Tier != target.Tier))
        {
            return EditorLoadAction.Refuse;
        }

        return EditorLoadAction.InPlace;
    }
}
