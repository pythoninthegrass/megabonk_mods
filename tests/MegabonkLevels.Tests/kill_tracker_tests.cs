using System.Collections.Generic;

namespace MegabonkLevels.Tests;

public class KillTrackerTests
{
    private const float Floor = -60f;
    private const float RetryAfter = 2f;

    private static KillTracker NewTracker() => new(RetryAfter);

    // The watcher keys its candidates by actor id, so a later reading of the same actor overwrites the earlier one.
    private static Dictionary<uint, float> Candidates(params (uint Id, float Y)[] readings)
    {
        var lowestById = new Dictionary<uint, float>();
        foreach (var (id, y) in readings)
        {
            lowestById[id] = y;
        }

        return lowestById;
    }

    [Fact]
    public void Select_FallenEnemyNeverKilled_ReturnsFirstAttempt()
    {
        var picks = NewTracker().Select(Candidates((1u, -61f)), Floor, now: 0f);

        Assert.Equal(new[] { (1u, 1) }, picks);
    }

    [Fact]
    public void Select_EnemyAtOrAboveTheFloor_IsNotReturned()
    {
        var picks = NewTracker().Select(Candidates((1u, -60f), (2u, 10f)), Floor, now: 0f);

        Assert.Empty(picks);
    }

    [Fact]
    public void Select_SameEnemyBeforeRetryWindow_IsNotReturnedAgain()
    {
        var tracker = NewTracker();
        tracker.Select(Candidates((1u, -61f)), Floor, now: 0f);

        var picks = tracker.Select(Candidates((1u, -70f)), Floor, now: 0.25f);

        Assert.Empty(picks);
    }

    [Fact]
    public void Select_EnemyStillPresentAfterRetryWindow_IsReturnedWithNextAttempt()
    {
        var tracker = NewTracker();
        tracker.Select(Candidates((1u, -61f)), Floor, now: 0f);

        var picks = tracker.Select(Candidates((1u, -61f)), Floor, now: RetryAfter);

        Assert.Equal(new[] { (1u, 2) }, picks);
    }

    [Fact]
    public void Select_EnemyThatLeftTheCandidates_IsForgotten()
    {
        var tracker = NewTracker();
        tracker.Select(Candidates((1u, -61f)), Floor, now: 0f);
        tracker.Select(Candidates(), Floor, now: 0.25f);

        var picks = tracker.Select(Candidates((1u, -61f)), Floor, now: 0.5f);

        Assert.Equal(new[] { (1u, 1) }, picks);
    }

    [Fact]
    public void Select_SameIdInTwoSources_IsReturnedOnce()
    {
        var picks = NewTracker().Select(Candidates((7u, -61f), (7u, -65f)), Floor, now: 0f);

        Assert.Equal(new[] { (7u, 1) }, picks);
    }

    [Fact]
    public void Select_EnemyThatRecoveredAboveTheFloor_ResetsItsAttempts()
    {
        var tracker = NewTracker();
        tracker.Select(Candidates((1u, -61f)), Floor, now: 0f);
        tracker.Select(Candidates((1u, 5f)), Floor, now: 1f);

        var picks = tracker.Select(Candidates((1u, -61f)), Floor, now: 1.25f);

        Assert.Equal(new[] { (1u, 1) }, picks);
    }

    [Fact]
    public void Select_ActorsFarAboveTheFloor_AreNotTrackedBetweenChecks()
    {
        var tracker = NewTracker();
        tracker.Select(Candidates((1u, -61f)), Floor, now: 0f);

        var picks = tracker.Select(Candidates((1u, 40f)), Floor, now: 0.25f);

        Assert.Empty(picks);
        Assert.Equal(new[] { (1u, 1) }, tracker.Select(Candidates((1u, -61f)), Floor, now: 0.5f));
    }
}
