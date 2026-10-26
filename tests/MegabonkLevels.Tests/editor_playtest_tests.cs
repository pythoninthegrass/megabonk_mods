namespace MegabonkLevels.Tests;

// Tests for the editor playtest round-trip (TASK-005.06): preserving the undo/redo session across
// the reload and restoring it on return. Unity-free pieces only.
public class EditorPlaytestTests
{
    private static void ApplyOp(EditorEditSession session, EditOp op, LevelState state)
    {
        var plan = EditCommandPlanner.Plan(op, state, nextPlacementId: 0, liveTransformFallback: null);
        session.Apply(plan, _ => true);
    }

    [Fact]
    public void CurrentEdits_ExcludesUndoneEdits_SoPlaytestSavesTheLiveList()
    {
        var state = new LevelState();
        var session = new EditorEditSession();
        ApplyOp(session, new AddTile(1, 1, 1).ToEditOp(), state);
        ApplyOp(session, new AddTile(2, 2, 2).ToEditOp(), state);
        session.Undo(_ => true);

        Assert.Single(session.CurrentEdits);
    }

    [Fact]
    public void Coordinator_Restore_PreservesUndoAndRedo()
    {
        var state = new LevelState();
        var session = new EditorEditSession();
        ApplyOp(session, new AddTile(1, 1, 1).ToEditOp(), state);
        ApplyOp(session, new AddTile(2, 2, 2).ToEditOp(), state);
        session.Undo(_ => true); // one op back on redo

        var coordinator = new PlaytestCoordinator();
        coordinator.Begin(session, lastSavedEditCount: 1);
        Assert.True(coordinator.Active);

        Assert.True(coordinator.TryRestore(out var restored, out var lastSaved));
        Assert.False(coordinator.Active);
        Assert.Equal(1, lastSaved);

        Assert.Same(session, restored);
        Assert.True(restored.CanUndo);
        Assert.True(restored.CanRedo);
    }

    [Fact]
    public void Coordinator_Discard_ClearsThePreservedSession()
    {
        var coordinator = new PlaytestCoordinator();
        coordinator.Begin(new EditorEditSession(), lastSavedEditCount: 0);
        coordinator.Discard();

        Assert.False(coordinator.Active);
        Assert.False(coordinator.TryRestore(out var session, out var lastSaved));
        Assert.Null(session);
    }

    [Fact]
    public void Pick_WithActivePlaytest_RestoresThePreservedSession()
    {
        var preserved = new EditorEditSession();
        var coordinator = new PlaytestCoordinator();
        coordinator.Begin(preserved, lastSavedEditCount: 3);

        var current = new EditorEditSession();
        var applied = EditorSessionPick.Pick(coordinator, currentGeneration: 5, currentSession: current, currentRunGeneration: 5, seedEdits: Array.Empty<EditOp>(), out var session, out var runGeneration, out var lastSaved);

        Assert.True(applied);
        Assert.Same(preserved, session);
        Assert.Equal(5, runGeneration);
        Assert.Equal(3, lastSaved);
    }

    [Fact]
    public void Pick_WhenGenerationChanged_ResetsFromSeed()
    {
        var coordinator = new PlaytestCoordinator(); // never begun
        var current = new EditorEditSession();
        var seed = new[] { new AddTile(0, 0, 1).ToEditOp() };

        var applied = EditorSessionPick.Pick(coordinator, currentGeneration: 6, currentSession: current, currentRunGeneration: 5, seedEdits: seed, out var session, out var runGeneration, out var lastSaved);

        Assert.True(applied);
        Assert.NotSame(current, session);
        Assert.Equal(6, runGeneration);
        Assert.Equal(1, lastSaved);
    }

    [Fact]
    public void Pick_WhenUnchanged_KeepsTheCurrentSession()
    {
        var coordinator = new PlaytestCoordinator();
        var current = new EditorEditSession();

        var applied = EditorSessionPick.Pick(coordinator, currentGeneration: 5, currentSession: current, currentRunGeneration: 5, seedEdits: Array.Empty<EditOp>(), out var session, out var runGeneration, out var lastSaved);

        Assert.False(applied);
        Assert.Same(current, session);
    }

    [Fact]
    public void Pick_AfterDiscard_FallsThroughToTheNormalReset()
    {
        var coordinator = new PlaytestCoordinator();
        coordinator.Begin(new EditorEditSession(), lastSavedEditCount: 0);
        coordinator.Discard();

        var current = new EditorEditSession();
        var applied = EditorSessionPick.Pick(coordinator, currentGeneration: 5, currentSession: current, currentRunGeneration: 5, seedEdits: Array.Empty<EditOp>(), out var session, out var runGeneration, out var lastSaved);

        Assert.False(applied);
        Assert.Same(current, session);
    }
}
