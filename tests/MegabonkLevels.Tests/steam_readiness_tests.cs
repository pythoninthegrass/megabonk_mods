namespace MegabonkLevels.Tests;

public class SteamReadinessTests
{
    private const string NotInitializedFault = "System.InvalidOperationException: Steamworks is not initialized.";

    [Fact]
    public void Probe_WhenBuildIdReads_ReportsReadyWithBuildId()
    {
        var readiness = SteamReadiness.Probe(() => "21750826");

        Assert.True(readiness.Ready);
        Assert.Equal("21750826", readiness.BuildId);
    }

    [Fact]
    public void Probe_WhenSteamworksNotInitialized_ReportsNotReady()
    {
        var readiness = SteamReadiness.Probe(() => throw new InvalidOperationException(NotInitializedFault));

        Assert.False(readiness.Ready);
        Assert.Null(readiness.BuildId);
    }

    [Fact]
    public void Probe_WhenAnotherFaultOccurs_Propagates()
    {
        Assert.Throws<InvalidOperationException>(() => SteamReadiness.Probe(() => throw new InvalidOperationException("something else")));
    }

    [Fact]
    public void Probe_WhenGuardedAccessorReturnsNull_ReportsNotReady()
    {
        var readiness = SteamReadiness.Probe(() => null);

        Assert.False(readiness.Ready);
        Assert.Null(readiness.BuildId);
        Assert.Equal(SteamReadiness.ReasonClientNotInitialized, readiness.Reason);
    }

    [Fact]
    public void Probe_WhenSteamIsNotRunning_ReportsSteamNotRunningReason()
    {
        var readiness = SteamReadiness.Probe(() => null, () => false);

        Assert.Equal(SteamReadiness.ReasonSteamNotRunning, readiness.Reason);
    }

    [Fact]
    public void Probe_WhenSteamRunsButClientIsUnavailable_ReportsClientNotInitialized()
    {
        var readiness = SteamReadiness.Probe(() => null, () => true);

        Assert.Equal(SteamReadiness.ReasonClientNotInitialized, readiness.Reason);
    }

    [Fact]
    public void Probe_WhenSteamRunningIsUnknown_ReportsTheFaultItSaw()
    {
        var readiness = SteamReadiness.Probe(() => null, () => null);

        Assert.Equal(SteamReadiness.ReasonClientNotInitialized, readiness.Reason);
    }

    [Fact]
    public void Probe_WhenBuildIdReads_DoesNotConsultSteamRunning()
    {
        var readiness = SteamReadiness.Probe(() => "21750826", () => throw new InvalidOperationException("never called"));

        Assert.True(readiness.Ready);
    }

    [Fact]
    public void Probe_WhenSteamRunningAnswerThrows_FallsBackToTheClientReason()
    {
        var readiness = SteamReadiness.Probe(() => null, () => throw new InvalidOperationException("no entry point"));

        Assert.False(readiness.Ready);
        Assert.Equal(SteamReadiness.ReasonClientNotInitialized, readiness.Reason);
    }

    [Fact]
    public void IsNotInitialized_WhenMessageCarriesTheInteropFault_ReturnsTrue()
    {
        Assert.True(SteamReadiness.IsNotInitialized(new InvalidOperationException(NotInitializedFault)));
    }

    [Fact]
    public void IsNotInitialized_ForAnyOtherFault_ReturnsFalse()
    {
        Assert.False(SteamReadiness.IsNotInitialized(new InvalidOperationException("something else")));
        Assert.False(SteamReadiness.IsNotInitialized(null));
    }

    [Fact]
    public void ToJson_WhenReady_IncludesReadyAndBuildId()
    {
        var json = new SteamReadiness(true, "21750826").ToJson();

        Assert.True((bool?)json["ready"]);
        Assert.Equal("21750826", (string?)json["buildId"]);
    }

    [Fact]
    public void ToJson_WhenNotReady_HasReadyFalseAndNoBuildId()
    {
        var json = new SteamReadiness(false, null).ToJson();

        Assert.False((bool?)json["ready"]);
        Assert.False(json.ContainsKey("buildId"));
        Assert.False(json.ContainsKey("reason"));
    }

    [Fact]
    public void ToJson_WhenNotReadyWithReason_IncludesTheReason()
    {
        var json = new SteamReadiness(false, null, SteamReadiness.ReasonSteamNotRunning).ToJson();

        Assert.False((bool?)json["ready"]);
        Assert.Equal(SteamReadiness.ReasonSteamNotRunning, (string?)json["reason"]);
    }
}
