namespace MegabonkLevels;

public enum EditorLoadAction
{
    InPlace,
    FreshRun,
    Refuse,
}

// How the editor's Load applies a file: a from-scratch level builds its own grid, so it needs a fresh run and its seed is irrelevant.
public static class EditorLoadPlan
{
    public static EditorLoadAction Decide(LevelFile? current, LevelFile target)
    {
        if (target.IsFromScratch || current is { IsFromScratch: true })
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
