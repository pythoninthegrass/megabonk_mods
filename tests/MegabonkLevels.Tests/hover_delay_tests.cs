namespace MegabonkLevels.Tests;

public class HoverDelayTests
{
    private static HoverDelay NewDelay(HoverActivity activity = null) => new(3f, 2f, activity ?? new HoverActivity());

    [Fact]
    public void Update_NotReadyUntilTheDelayHasPassedOnTheSameTarget()
    {
        var delay = NewDelay();

        Assert.False(delay.Update(2, 10f));
        Assert.False(delay.Update(2, 12.9f));
        Assert.True(delay.Update(2, 13f));
    }

    [Fact]
    public void Update_ChangingTargetRestartsTheDelay()
    {
        var delay = NewDelay();
        delay.Update(1, 10f);

        Assert.False(delay.Update(2, 12f));
        Assert.False(delay.Update(2, 14.9f));
        Assert.True(delay.Update(2, 15f));
    }

    [Fact]
    public void Update_NoTargetIsNeverReadyAndRestartsTheDelay()
    {
        var delay = NewDelay();
        delay.Update(1, 10f);

        Assert.False(delay.Update(null, 14f));
        Assert.False(delay.Update(1, 14.5f));
        Assert.True(delay.Update(1, 17.5f));
    }

    [Fact]
    public void Update_MovingToAnotherTargetWithinTheGraceKeepsItReady()
    {
        var delay = NewDelay();
        delay.Update(1, 10f);
        Assert.True(delay.Update(1, 13f));

        Assert.True(delay.Update(3, 13.1f));
        Assert.True(delay.Update(5, 14f));
    }

    [Fact]
    public void Update_GraceRunsFromTheLastTimeItWasReady()
    {
        var delay = NewDelay();
        delay.Update(1, 10f);
        delay.Update(1, 13f);
        delay.Update(null, 13.5f);

        Assert.True(delay.Update(2, 14.9f));
    }

    [Fact]
    public void Update_LeavingForLongerThanTheGraceRestartsTheDelay()
    {
        var delay = NewDelay();
        delay.Update(1, 10f);
        delay.Update(1, 13f);
        delay.Update(null, 13.5f);

        Assert.False(delay.Update(2, 15.1f));
        Assert.False(delay.Update(2, 18f));
        Assert.True(delay.Update(2, 18.1f));
    }

    [Fact]
    public void Update_GraceIsSharedThroughTheActivity()
    {
        var activity = new HoverActivity();
        var first = NewDelay(activity);
        var second = NewDelay(activity);
        first.Update(1, 10f);
        first.Update(1, 13f);

        Assert.True(second.Update(7, 14f));
    }
}
