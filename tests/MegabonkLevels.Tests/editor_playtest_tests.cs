namespace MegabonkLevels.Tests;

public class EditorPlaytestTests
{
    [Fact]
    public void Pick_GenerationFinishesWhileEditing_ReentryKeepsSubsequentEdits()
    {
        var early = new EditorEditSession();
        Assert.True(EditorSessionPick.Pick(6, early, 5, 0, Array.Empty<EditOp>(), out var live, out var generation, out var saved));
        var op = new AddTile(1, 1, 1).ToEditOp();
        live.Apply(EditCommandPlanner.Plan(op, new LevelState(), nextPlacementId: 0, liveTransformFallback: null), _ => true);
        Assert.False(EditorSessionPick.Pick(6, live, generation, saved, Array.Empty<EditOp>(), out var returned, out _, out _));
        Assert.Same(live, returned);
        Assert.True(returned.CanUndo);
        Assert.Single(returned.CurrentEdits);
    }

    [Fact]
    public void Pick_RepeatedSameRunToggles_PreserveHistoryAndSaveState()
    {
        var current = new EditorEditSession();
        var state = new LevelState();
        foreach (var op in new[] { new AddTile(1, 1, 1).ToEditOp(), new AddTile(2, 2, 2).ToEditOp() })
        {
            current.Apply(EditCommandPlanner.Plan(op, state, nextPlacementId: 0, liveTransformFallback: null), _ => true);
        }

        current.Undo(_ => true);
        for (var i = 0; i < 5; i++)
        {
            var changed = EditorSessionPick.Pick(5, current, 5, 2, Array.Empty<EditOp>(), out var session, out var generation, out var saved);
            Assert.False(changed);
            Assert.Same(current, session);
            Assert.Equal(5, generation);
            Assert.Equal(2, saved);
            Assert.True(session.CanUndo);
            Assert.True(session.CanRedo);
            Assert.Single(session.CurrentEdits);
        }

        Assert.True(current.Redo(_ => true));
        Assert.Equal(2, current.CurrentEdits.Count);
        Assert.True(current.Undo(_ => true));
    }

    [Fact]
    public void Pick_NewRun_ResetsHistoryFromSeed()
    {
        var current = new EditorEditSession();
        var seed = new[] { new AddTile(0, 0, 1).ToEditOp() };
        Assert.True(EditorSessionPick.Pick(6, current, 5, 3, seed, out var session, out var generation, out var saved));
        Assert.NotSame(current, session);
        Assert.Equal(6, generation);
        Assert.Equal(1, saved);
        Assert.Equal(seed, session.CurrentEdits);
        Assert.False(session.CanRedo);
    }

    [Fact]
    public void Pick_FirstEntry_CreatesSession()
    {
        Assert.True(EditorSessionPick.Pick(5, null!, -1, 0, Array.Empty<EditOp>(), out var session, out var generation, out var saved));
        Assert.NotNull(session);
        Assert.Equal(5, generation);
        Assert.Equal(0, saved);
    }
}
