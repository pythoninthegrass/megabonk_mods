namespace MegabonkLevels.Tests;

public class RadioPlaylistTests
{
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
}
