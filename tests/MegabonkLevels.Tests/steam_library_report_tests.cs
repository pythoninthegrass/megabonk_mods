using System.Text;

namespace MegabonkLevels.Tests;

public class SteamLibraryReportTests
{
    [Fact]
    public void Classify_WhenBytesCarryTheStubMarker_ReportsStub()
    {
        var bytes = Encoding.ASCII.GetBytes("prefix " + SteamLibraryReport.StubMarker + " suffix");

        Assert.Equal("stub", SteamLibraryReport.Classify(bytes));
    }

    [Fact]
    public void Classify_WithoutTheMarker_ReportsOriginal()
    {
        var bytes = Encoding.ASCII.GetBytes("Steam client, no marker here");

        Assert.Equal("original", SteamLibraryReport.Classify(bytes));
    }

    [Fact]
    public void Classify_WhenThereIsNoLibrary_ReportsMissing()
    {
        Assert.Equal("missing", SteamLibraryReport.Classify(null));
    }

    [Fact]
    public void Classify_WhenTheMarkerOnlyStraddlesTheEnd_ReportsOriginal()
    {
        var marker = Encoding.ASCII.GetBytes(SteamLibraryReport.StubMarker);
        var bytes = new byte[marker.Length - 1];
        marker.AsSpan(0, bytes.Length).CopyTo(bytes);

        Assert.Equal("original", SteamLibraryReport.Classify(bytes));
    }

    [Fact]
    public void FromGameRoot_WhenTheDirectoryHasNoPluginsLibrary_ReportsMissing()
    {
        var root = Path.Combine(Path.GetTempPath(), "megabonk-no-steam-library-" + Guid.NewGuid().ToString("N"));

        Assert.Equal("missing", SteamLibraryReport.FromGameRoot(root));
    }
}
