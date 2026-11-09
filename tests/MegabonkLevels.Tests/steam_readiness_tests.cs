namespace MegabonkLevels.Tests;

public class SteamReadinessTests
{
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
        var readiness = SteamReadiness.Probe(() => throw new InvalidOperationException("System.InvalidOperationException: Steamworks is not initialized."));

        Assert.False(readiness.Ready);
        Assert.Null(readiness.BuildId);
    }

    [Fact]
    public void Probe_WhenAnotherFaultOccurs_Propagates()
    {
        Assert.Throws<InvalidOperationException>(() => SteamReadiness.Probe(() => throw new InvalidOperationException("something else")));
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
    }
}
