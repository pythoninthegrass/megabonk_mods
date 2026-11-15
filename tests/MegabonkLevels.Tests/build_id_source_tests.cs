namespace MegabonkLevels.Tests;

public class BuildIdSourceTests
{
    [Fact]
    public void CurrentBuildId_WhenSteamworksAnswers_ReturnsTheId()
    {
        var source = new BuildIdSource(() => "21750826");

        Assert.Equal("21750826", source.CurrentBuildId());
    }

    [Fact]
    public void CurrentBuildId_WhenSteamworksNotInitialized_ReturnsNullWithoutThrowing()
    {
        var source = new BuildIdSource(() => throw new InvalidOperationException("System.InvalidOperationException: Steamworks is not initialized."));

        Assert.Null(source.CurrentBuildId());
    }

    [Fact]
    public void CurrentBuildId_WhenAnotherFaultOccurs_Propagates()
    {
        var source = new BuildIdSource(() => throw new InvalidOperationException("Access denied to Steam pipe"));

        Assert.Throws<InvalidOperationException>(() => source.CurrentBuildId());
    }

    [Fact]
    public void CurrentBuildId_WhenStillUnavailable_KeepsTryingInsteadOfCachingTheFailure()
    {
        var calls = 0;
        var source = new BuildIdSource(() =>
        {
            calls++;
            if (calls < 3)
            {
                throw new InvalidOperationException("Steamworks is not initialized.");
            }

            return "21750826";
        });

        Assert.Null(source.CurrentBuildId());
        Assert.Null(source.CurrentBuildId());
        Assert.Equal("21750826", source.CurrentBuildId());
    }

    [Fact]
    public void CurrentBuildId_WhenUnavailable_ReportsItOnceAcrossRepeatedReads()
    {
        var notices = 0;
        var source = new BuildIdSource(() => throw new InvalidOperationException("Steamworks is not initialized."), () => notices++);

        for (var i = 0; i < 5; i++)
        {
            Assert.Null(source.CurrentBuildId());
        }

        Assert.Equal(1, notices);
    }

    [Fact]
    public void CurrentBuildId_WhenReadSucceeds_DoesNotReportUnavailability()
    {
        var notices = 0;
        var source = new BuildIdSource(() => "21750826", () => notices++);

        source.CurrentBuildId();

        Assert.Equal(0, notices);
    }

    [Fact]
    public void CurrentBuildId_AfterTheIdReads_CachesItAndStopsCallingSteamworks()
    {
        var calls = 0;
        var source = new BuildIdSource(() =>
        {
            calls++;
            return "21750826";
        });

        Assert.Equal("21750826", source.CurrentBuildId());
        Assert.Equal("21750826", source.CurrentBuildId());
        Assert.Equal(1, calls);
    }
}
