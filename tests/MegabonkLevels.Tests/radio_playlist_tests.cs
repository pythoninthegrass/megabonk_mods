namespace MegabonkLevels.Tests;

public class RadioPlaylistTests
{
    [Fact]
    public void PreserveOrder_DeduplicatesContinuesAndWrapsWithoutSorting()
    {
        var playlist = RadioPlaylist.PreserveOrder(["6 Base", "06.01 One", "06.02 Two", "6 Base"]);

        playlist.StartAfter("06.01 One");

        Assert.Equal(new[] { "06.02 Two", "6 Base", "06.01 One" }, new[] { playlist.Next(), playlist.Next(), playlist.Next() });
    }

    [Fact]
    public void PreserveOrder_EmptyPlaylistReturnsNull()
    {
        Assert.Null(RadioPlaylist.PreserveOrder([]).Next());
    }

    [Fact]
    public void Next_FollowsClipNameOrderAndWraps()
    {
        var playlist = new RadioPlaylist(["02_Here_and_Now", "01_Police_Truck", "03_Vilified"]);

        Assert.Equal("01_Police_Truck", playlist.Next());
        Assert.Equal("02_Here_and_Now", playlist.Next());
        Assert.Equal("03_Vilified", playlist.Next());
        Assert.Equal("01_Police_Truck", playlist.Next());
    }

    [Fact]
    public void Next_WithNoClipsReturnsNull()
    {
        Assert.Null(new RadioPlaylist([]).Next());
    }

    [Fact]
    public void Constructor_IgnoresDuplicateClipNames()
    {
        var playlist = new RadioPlaylist(["01_A", "01_A", "02_B"]);

        Assert.Equal(["01_A", "02_B"], new[] { playlist.Next(), playlist.Next() });
    }

    [Fact]
    public void StartAfter_ContinuesFromTheClipThatIsAlreadyPlaying()
    {
        var playlist = new RadioPlaylist(["03_C", "01_A", "02_B", "04_D"]);

        playlist.StartAfter("02_B");

        Assert.Equal(["03_C", "04_D", "01_A"], new[] { playlist.Next(), playlist.Next(), playlist.Next() });
    }

    [Fact]
    public void StartAfter_AnUnknownClipLeavesTheStartAtTheFirstClip()
    {
        var playlist = new RadioPlaylist(["01_A", "02_B"]);

        playlist.StartAfter("99_missing");

        Assert.Equal("01_A", playlist.Next());
    }

    [Theory]
    [InlineData(150f, 0.4f, true)]
    [InlineData(30.2f, 30.3f, false)]
    [InlineData(0f, 0.1f, false)]
    [InlineData(185f, 184.9f, false)]
    public void LoopWrap_IsTrueWhenPlaybackJumpsBackToTheStart(float previous, float current, bool wrapped)
    {
        Assert.Equal(wrapped, RadioPlaylist.LoopWrapped(previous, current));
    }
}
