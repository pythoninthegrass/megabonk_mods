namespace MegabonkLevels.Tests;

public class KillTrackerTests
{
    private const float Floor = -60f;
    private const float RetryAfter = 2f;

    private static KillTracker NewTracker() => new(RetryAfter);

    [Fact]
    public void Select_FallenEnemyNeverKilled_ReturnsFirstAttempt()
    {
        var picks = NewTracker().Select(new[] { (1u, -61f) }, Floor, now: 0f);

        Assert.Equal(new[] { (1u, 1) }, picks);
    }

    [Fact]
    public void Select_EnemyAtOrAboveTheFloor_IsNotReturned()
    {
        var picks = NewTracker().Select(new[] { (1u, -60f), (2u, 10f) }, Floor, now: 0f);

        Assert.Empty(picks);
    }

    [Fact]
    public void Select_SameEnemyBeforeRetryWindow_IsNotReturnedAgain()
    {
        var tracker = NewTracker();
        tracker.Select(new[] { (1u, -61f) }, Floor, now: 0f);

        var picks = tracker.Select(new[] { (1u, -70f) }, Floor, now: 0.25f);

        Assert.Empty(picks);
    }

    [Fact]
    public void Select_EnemyStillPresentAfterRetryWindow_IsReturnedWithNextAttempt()
    {
        var tracker = NewTracker();
        tracker.Select(new[] { (1u, -61f) }, Floor, now: 0f);

        var picks = tracker.Select(new[] { (1u, -61f) }, Floor, now: RetryAfter);

        Assert.Equal(new[] { (1u, 2) }, picks);
    }

    [Fact]
    public void Select_EnemyThatLeftTheCandidates_IsForgotten()
    {
        var tracker = NewTracker();
        tracker.Select(new[] { (1u, -61f) }, Floor, now: 0f);
        tracker.Select(Array.Empty<(uint, float)>(), Floor, now: 0.25f);

        var picks = tracker.Select(new[] { (1u, -61f) }, Floor, now: 0.5f);

        Assert.Equal(new[] { (1u, 1) }, picks);
    }

    [Fact]
    public void Select_SameIdInTwoSources_IsReturnedOnce()
    {
        var picks = NewTracker().Select(new[] { (7u, -61f), (7u, -61f) }, Floor, now: 0f);

        Assert.Equal(new[] { (7u, 1) }, picks);
    }

    [Fact]
    public void Select_EnemyThatRecoveredAboveTheFloor_ResetsItsAttempts()
    {
        var tracker = NewTracker();
        tracker.Select(new[] { (1u, -61f) }, Floor, now: 0f);
        tracker.Select(new[] { (1u, 5f) }, Floor, now: 1f);

        var picks = tracker.Select(new[] { (1u, -61f) }, Floor, now: 1.25f);

        Assert.Equal(new[] { (1u, 1) }, picks);
    }
}
