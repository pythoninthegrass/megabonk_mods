using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels.Tests;

public class StartupGateTests
{
    private const float Timeout = 8f;

    [Fact]
    public void VanillaRun_NeverCoversAndIgnoresEveryLaterEvent()
    {
        var gate = New();
        gate.RunStarted(false, 0f);

        Assert.Equal(StartupGatePhase.Idle, gate.Phase);
        Assert.Empty(gate.Drain());

        gate.GameSpawnedPlayer(1f);
        gate.ContentReady(2f);
        gate.Tick(3f);
        gate.Tick(100f);

        Assert.Empty(gate.Drain());
        Assert.False(gate.ShouldAttemptPlace);
        Assert.False(gate.ShouldHoldPlayer);
    }

    [Fact]
    public void CustomRun_CoversAsSoonAsItStarts()
    {
        var gate = New();
        gate.RunStarted(true, 0f);

        Assert.Equal(StartupGatePhase.Covering, gate.Phase);
        Assert.Equal(new[] { StartupGateCommandKind.ShowCover }, Kinds(gate));
    }

    [Fact]
    public void Startup_CoversThenHoldsThenPlacesThenOpens()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.GameSpawnedPlayer(1f);
        gate.ContentReady(5f);

        Assert.True(gate.ShouldAttemptPlace);
        gate.PlacementCompleted(5f);

        Assert.Equal(StartupGatePhase.Open, gate.Phase);
        Assert.True(gate.Placed);
        Assert.Equal(
            new[]
            {
                StartupGateCommandKind.ShowCover,
                StartupGateCommandKind.HoldPlayer,
                StartupGateCommandKind.PlacePlayer,
                StartupGateCommandKind.ReleaseHold,
                StartupGateCommandKind.HideCover,
            },
            Kinds(gate));
    }

    [Fact]
    public void Placement_IsNotOwedBeforeTheContentIsReady()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.GameSpawnedPlayer(1f);
        gate.Drain();

        for (var t = 1f; t < 4f; t += 0.1f)
        {
            gate.Tick(t);
        }

        Assert.False(gate.ShouldAttemptPlace);
        Assert.Empty(gate.Drain());
    }

    [Fact]
    public void LateGameSpawn_PlacesOnceAndLaterTicksNeverMoveThePlayerAgain()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.GameSpawnedPlayer(1f);
        gate.ContentReady(5f);
        gate.PlacementCompleted(5f);
        gate.Drain();

        gate.GameSpawnedPlayer(20f);
        Assert.True(gate.ShouldAttemptPlace);
        gate.PlacementCompleted(20f);

        Assert.Equal(new[] { StartupGateCommandKind.PlacePlayer }, Kinds(gate));

        for (var t = 20f; t < 40f; t += 0.1f)
        {
            gate.Tick(t);
        }

        Assert.False(gate.ShouldAttemptPlace);
        Assert.Empty(gate.Drain());
    }

    [Fact]
    public void SpawnEventsArrivingTogether_AskForOnePlacement()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.ContentReady(1f);
        gate.PlacementCompleted(1f);
        gate.Drain();

        gate.GameSpawnedPlayer(10f);
        gate.GameSpawnedPlayer(10.004f);
        gate.GameSpawnedPlayer(10.008f);

        Assert.Equal(new[] { StartupGateCommandKind.PlacePlayer }, Kinds(gate));
    }

    [Fact]
    public void SpawnEventsFarApart_AskForTheirOwnPlacement()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.ContentReady(1f);
        gate.PlacementCompleted(1f);
        gate.Drain();

        gate.GameSpawnedPlayer(10f);
        gate.PlacementCompleted(10f);
        gate.GameSpawnedPlayer(20f);

        Assert.True(gate.ShouldAttemptPlace);
        Assert.Equal(new[] { StartupGateCommandKind.PlacePlayer, StartupGateCommandKind.PlacePlayer }, Kinds(gate));
    }

    [Fact]
    public void MissingPlayer_KeepsAskingAtTheRetryRateUntilOneShowsUp()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.ContentReady(1f);

        Assert.True(gate.ShouldAttemptPlace);
        gate.PlaceAttemptFailed("no player", 1f);
        Assert.False(gate.ShouldAttemptPlace);

        gate.Tick(1.05f);
        Assert.False(gate.ShouldAttemptPlace);

        gate.Tick(1.11f);
        Assert.True(gate.ShouldAttemptPlace);

        gate.PlacementCompleted(1.11f);
        Assert.False(gate.ShouldAttemptPlace);
        Assert.Equal(StartupGatePhase.Open, gate.Phase);
    }

    [Fact]
    public void MissingPlayer_GivesUpAfterTheAttemptCapAndStillPlacesALatePlayer()
    {
        var gate = New(timeoutSeconds: Timeout, maxPlaceAttempts: 3);
        gate.RunStarted(true, 0f);
        gate.ContentReady(1f);

        for (var i = 0; i < 3; i++)
        {
            gate.PlaceAttemptFailed("no player", 1f + i);
        }

        Assert.False(gate.ShouldAttemptPlace);
        Assert.Single(Kinds(gate), k => k == StartupGateCommandKind.Log);

        gate.GameSpawnedPlayer(20f);
        Assert.True(gate.ShouldAttemptPlace);
    }

    [Fact]
    public void Timeout_ReleasesCoverAndHoldOnce_AndLateContentStillPlaces()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.GameSpawnedPlayer(1f);
        gate.Drain();

        gate.Tick(8.01f);

        Assert.Equal(StartupGatePhase.Open, gate.Phase);
        Assert.False(gate.ShouldHoldPlayer);
        Assert.Equal(
            new[]
            {
                StartupGateCommandKind.ReleaseHold,
                StartupGateCommandKind.HideCover,
                StartupGateCommandKind.Log,
            },
            Kinds(gate));

        gate.Tick(9f);
        gate.Tick(30f);
        Assert.Empty(gate.Drain());

        gate.ContentReady(10f);
        Assert.True(gate.ShouldAttemptPlace);
        Assert.Equal(new[] { StartupGateCommandKind.PlacePlayer }, Kinds(gate));
    }

    [Fact]
    public void Timeout_WhileStillCoveringWithoutAPlayer_LeavesTheRunPlayable()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.Drain();

        gate.Tick(8.01f);

        Assert.Equal(StartupGatePhase.Open, gate.Phase);
        Assert.Equal(new[] { StartupGateCommandKind.HideCover, StartupGateCommandKind.Log }, Kinds(gate));
    }

    [Fact]
    public void Cancelled_StartDropsTheCoverAndRefusesToPlaceAfterwards()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.Drain();

        gate.Cancelled("load cancelled");

        Assert.Equal(StartupGatePhase.Idle, gate.Phase);
        Assert.Equal(new[] { StartupGateCommandKind.HideCover, StartupGateCommandKind.Log }, Kinds(gate));

        gate.ContentReady(1f);
        gate.GameSpawnedPlayer(2f);
        gate.Tick(3f);

        Assert.Empty(gate.Drain());
        Assert.False(gate.ShouldAttemptPlace);
    }

    [Fact]
    public void Failed_Start_WhileHolding_ReleasesBothCoverAndHold()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.GameSpawnedPlayer(1f);
        gate.Drain();

        gate.Failed("StartNewMap threw");

        Assert.Equal(StartupGatePhase.Idle, gate.Phase);
        Assert.Equal(
            new[]
            {
                StartupGateCommandKind.ReleaseHold,
                StartupGateCommandKind.HideCover,
                StartupGateCommandKind.Log,
            },
            Kinds(gate));
    }

    [Fact]
    public void Failure_WithNothingInFlight_ReportsNothing()
    {
        var gate = New();

        gate.Failed("nothing running");
        gate.Cancelled("nothing running");

        Assert.Empty(gate.Drain());
    }

    [Fact]
    public void VanillaRun_WhileACustomCoverIsUp_DropsTheCover()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.GameSpawnedPlayer(1f);
        gate.Drain();

        gate.RunStarted(false, 2f);

        Assert.Equal(StartupGatePhase.Idle, gate.Phase);
        Assert.Equal(new[] { StartupGateCommandKind.ReleaseHold, StartupGateCommandKind.HideCover }, Kinds(gate));
    }

    [Fact]
    public void NextCustomRun_CoversAgainAfterThePreviousOneOpened()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.ContentReady(1f);
        gate.PlacementCompleted(1f);
        gate.Drain();

        gate.RunStarted(true, 30f);

        Assert.Equal(StartupGatePhase.Covering, gate.Phase);
        Assert.False(gate.Placed);
        Assert.Equal(new[] { StartupGateCommandKind.ShowCover }, Kinds(gate));
    }

    [Fact]
    public void Hold_IsIssuedOnceEvenWhenTheGameSpawnsAgainWhileCovered()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.GameSpawnedPlayer(1f);
        gate.GameSpawnedPlayer(2f);
        gate.GameSpawnedPlayer(3f);

        Assert.Equal(new[] { StartupGateCommandKind.ShowCover, StartupGateCommandKind.HoldPlayer }, Kinds(gate));
    }

    [Fact]
    public void Hold_IsNotTakenAgainAfterTheTimeoutReleasedIt()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.GameSpawnedPlayer(1f);
        gate.Tick(8.01f);
        gate.Drain();

        gate.GameSpawnedPlayer(9f);

        Assert.False(gate.ShouldHoldPlayer);
        Assert.Equal(new[] { StartupGateCommandKind.PlacePlayer }, Kinds(gate));
    }

    [Fact]
    public void Drain_EmptiesTheRecordedCommands()
    {
        var gate = New();
        gate.RunStarted(true, 0f);

        Assert.NotEmpty(gate.Drain());
        Assert.Empty(gate.Drain());
    }

    [Theory]
    [InlineData(null, 8f)]
    [InlineData("", 8f)]
    [InlineData("invalid", 8f)]
    [InlineData("0", 8f)]
    [InlineData("-1", 8f)]
    [InlineData("NaN", 8f)]
    [InlineData("Infinity", 8f)]
    [InlineData("1e100", 8f)]
    [InlineData("30", 30f)]
    [InlineData("12.5", 12.5f)]
    public void TimeoutSetting_RequiresPositiveFiniteInvariantSeconds(string value, float expected)
    {
        Assert.Equal(expected, StartupGate.ParseTimeoutSeconds(value));
    }

    [Fact]
    public void Progress_RenewsTheInactivityDeadline_ThenStallingReleasesBoth()
    {
        var gate = New(timeoutSeconds: 12f);
        gate.RunStarted(true, 0f);
        gate.GameSpawnedPlayer(1f);
        gate.Progress(11f);
        gate.Tick(20f);
        Assert.Equal(StartupGatePhase.Covering, gate.Phase);
        Assert.True(gate.ShouldHoldPlayer);
        gate.Progress(22f);
        gate.Tick(33f);
        Assert.Equal(StartupGatePhase.Covering, gate.Phase);
        gate.Drain();

        gate.Tick(34.01f);
        Assert.False(gate.ShouldHoldPlayer);
        Assert.Equal(new[] { StartupGateCommandKind.ReleaseHold, StartupGateCommandKind.HideCover, StartupGateCommandKind.Log }, Kinds(gate));
    }

    [Fact]
    public void ContentReady_RenewsDeadlineForPlacement_ButRetriesDoNot()
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        gate.ContentReady(7f);
        gate.Tick(14f);
        Assert.Equal(StartupGatePhase.Placing, gate.Phase);
        gate.PlaceAttemptFailed("no player", 14f);
        gate.Tick(15.01f);
        Assert.Equal(StartupGatePhase.Open, gate.Phase);
    }

    [Theory]
    [InlineData("timeout")]
    [InlineData("cancel")]
    [InlineData("vanilla")]
    [InlineData("placed")]
    public void Progress_AfterReleaseDoesNotReopenCover(string release)
    {
        var gate = New();
        gate.RunStarted(true, 0f);
        switch (release)
        {
            case "timeout": gate.Tick(9f); break;
            case "cancel": gate.Cancelled("cancel"); break;
            case "vanilla": gate.RunStarted(false, 1f); break;
            case "placed": gate.ContentReady(1f); gate.PlacementCompleted(1f); break;
        }
        gate.Drain();
        gate.Progress(20f);
        gate.Tick(21f);
        Assert.Empty(gate.Drain());
        Assert.False(gate.ShouldHoldPlayer);
        Assert.False(gate.ShouldAttemptPlace);
    }

    private static StartupGate New(float timeoutSeconds = Timeout, int maxPlaceAttempts = 100) =>
        new StartupGate(timeoutSeconds: timeoutSeconds, spawnBurstSeconds: 0.25f, placeRetrySeconds: 0.1f, maxPlaceAttempts: maxPlaceAttempts);

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void PortalAndContent_MustBothFinishBeforePlacement(bool contentFirst)
    {
        var gate = New();
        gate.RunStarted(true, 0f, waitForPortal: true);
        gate.GameSpawnedPlayer(1f);
        if (contentFirst) gate.ContentReady(2f);
        else gate.PortalClosed(2f);
        Assert.False(gate.ShouldAttemptPlace);
        Assert.True(gate.ShouldHoldPlayer);
        Assert.DoesNotContain(StartupGateCommandKind.HideCover, Kinds(gate));

        if (contentFirst) gate.PortalClosed(5f);
        else gate.ContentReady(5f);
        Assert.True(gate.ShouldAttemptPlace);
        gate.PlacementCompleted(5f);
        Assert.False(gate.ShouldHoldPlayer);
        Assert.Equal(StartupGatePhase.Open, gate.Phase);
        Assert.Contains(StartupGateCommandKind.HideCover, Kinds(gate));

        gate.PortalClosed(6f);
        gate.Tick(7f);
        Assert.False(gate.ShouldAttemptPlace);
        Assert.Empty(gate.Drain());
    }

    [Fact]
    public void SpawnBursts_WhilePortalOwnsPosition_CannotPlaceEarly()
    {
        var gate = New();
        gate.RunStarted(true, 0f, waitForPortal: true);
        gate.ContentReady(1f);
        gate.GameSpawnedPlayer(2f);
        gate.GameSpawnedPlayer(3f);
        gate.Tick(4f);
        Assert.False(gate.ShouldAttemptPlace);
        gate.PortalClosed(5f);
        Assert.True(gate.ShouldAttemptPlace);
        Assert.Single(Kinds(gate), k => k == StartupGateCommandKind.PlacePlayer);
    }

    [Fact]
    public void MissingPortal_TimesOutAndLateCompletionStillPermitsOnePlacement()
    {
        var gate = New();
        gate.RunStarted(true, 0f, waitForPortal: true);
        gate.GameSpawnedPlayer(1f);
        gate.ContentReady(2f);
        gate.Tick(10.1f);
        Assert.False(gate.ShouldHoldPlayer);
        Assert.False(gate.ShouldAttemptPlace);
        Assert.Contains(StartupGateCommandKind.HideCover, Kinds(gate));
        gate.PortalClosed(12f);
        Assert.True(gate.ShouldAttemptPlace);
        gate.PlacementCompleted(12f);
        gate.PortalClosed(13f);
        Assert.False(gate.ShouldAttemptPlace);
        Assert.DoesNotContain(StartupGateCommandKind.ShowCover, Kinds(gate));
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void AbortedPortalWait_IgnoresLateCompletion(bool vanilla)
    {
        var gate = New();
        gate.RunStarted(true, 0f, waitForPortal: true);
        gate.ContentReady(1f);
        if (vanilla) gate.RunStarted(false, 2f);
        else gate.Cancelled("cancel");
        gate.PortalClosed(3f);
        Assert.False(gate.ShouldAttemptPlace);
        Assert.False(gate.ShouldHoldPlayer);
        Assert.Equal(StartupGatePhase.Idle, gate.Phase);
    }

    private static List<StartupGateCommandKind> Kinds(StartupGate gate) => gate.Drain().Select(c => c.Kind).ToList();
}
