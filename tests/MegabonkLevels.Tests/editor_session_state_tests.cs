namespace MegabonkLevels.Tests;

public class EditorSessionStateTests
{
    [Fact]
    public void NewState_IsInactive()
    {
        Assert.False(new EditorSessionState().Active);
    }

    [Fact]
    public void Enter_ActivatesTheSession()
    {
        var state = new EditorSessionState();

        Assert.True(state.Enter(gamePausedBefore: false));
        Assert.True(state.Active);
    }

    [Fact]
    public void Enter_WhileActive_IsANoOpAndKeepsTheFirstPausedFlag()
    {
        var state = new EditorSessionState();
        state.Enter(gamePausedBefore: false);

        Assert.False(state.Enter(gamePausedBefore: true));

        Assert.True(state.TryExit(out var shouldUnpause));
        Assert.True(shouldUnpause);
    }

    [Fact]
    public void TryExit_WithoutEnter_IsANoOp()
    {
        var state = new EditorSessionState();

        Assert.False(state.TryExit(out var shouldUnpause));
        Assert.False(shouldUnpause);
    }

    [Fact]
    public void TryExit_AfterEnteringWhileRunning_Unpauses()
    {
        var state = new EditorSessionState();
        state.Enter(gamePausedBefore: false);

        Assert.True(state.TryExit(out var shouldUnpause));
        Assert.True(shouldUnpause);
        Assert.False(state.Active);
    }

    [Fact]
    public void TryExit_AfterEnteringWhileAlreadyPaused_DoesNotUnpause()
    {
        var state = new EditorSessionState();
        state.Enter(gamePausedBefore: true);

        Assert.True(state.TryExit(out var shouldUnpause));
        Assert.False(shouldUnpause);
    }

    [Fact]
    public void TryExit_Twice_SecondCallIsANoOp()
    {
        var state = new EditorSessionState();
        state.Enter(gamePausedBefore: false);
        state.TryExit(out _);

        Assert.False(state.TryExit(out var shouldUnpause));
        Assert.False(shouldUnpause);
    }

    [Fact]
    public void RepeatedCycles_EachRestoreTheirOwnPausedFlag()
    {
        var state = new EditorSessionState();

        for (var i = 0; i < 10; i++)
        {
            var pausedBefore = i % 2 == 1;
            Assert.True(state.Enter(pausedBefore));
            Assert.True(state.TryExit(out var shouldUnpause));
            Assert.Equal(!pausedBefore, shouldUnpause);
            Assert.False(state.Active);
        }
    }
}
