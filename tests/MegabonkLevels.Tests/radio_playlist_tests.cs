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

    [Fact]
    public void Names_AreTheOrderedClipsAndCountMatches()
    {
        var playlist = new RadioPlaylist(["02_B", "01_A", "02_B"]);

        Assert.Equal(["01_A", "02_B"], playlist.Names);
        Assert.Equal(2, playlist.Count);
    }

    [Fact]
    public void CurrentNumber_IsZeroUntilAClipIsChosen_ThenTracksTheLastClipPlayed()
    {
        var playlist = new RadioPlaylist(["01_A", "02_B", "03_C"]);

        Assert.Equal(0, playlist.CurrentNumber);
        playlist.Next();
        Assert.Equal(1, playlist.CurrentNumber);
        playlist.Next();
        Assert.Equal(2, playlist.CurrentNumber);
    }

    [Fact]
    public void CurrentNumber_FollowsStartAfter()
    {
        var playlist = new RadioPlaylist(["01_A", "02_B", "03_C"]);

        playlist.StartAfter("02_B");

        Assert.Equal(2, playlist.CurrentNumber);
    }

    [Fact]
    public void Previous_StepsBackAndWrapsToTheLastClip()
    {
        var playlist = new RadioPlaylist(["01_A", "02_B", "03_C"]);
        playlist.StartAfter("02_B");

        Assert.Equal("01_A", playlist.Previous());
        Assert.Equal("03_C", playlist.Previous());
        Assert.Equal("02_B", playlist.Previous());
    }

    [Fact]
    public void Previous_WithNothingPlayedStartsAtTheLastClip()
    {
        Assert.Equal("03_C", new RadioPlaylist(["01_A", "02_B", "03_C"]).Previous());
    }

    [Fact]
    public void Previous_WithNoClipsReturnsNull()
    {
        Assert.Null(new RadioPlaylist([]).Previous());
    }

    [Fact]
    public void Next_AfterPreviousContinuesFromTheClipChosen()
    {
        var playlist = new RadioPlaylist(["01_A", "02_B", "03_C"]);
        playlist.StartAfter("03_C");

        Assert.Equal("02_B", playlist.Previous());
        Assert.Equal("03_C", playlist.Next());
        Assert.Equal("01_A", playlist.Next());
    }

    [Theory]
    [InlineData(1, "01_A")]
    [InlineData(3, "03_C")]
    public void Select_PicksTheOneBasedClip(int number, string clip)
    {
        var playlist = new RadioPlaylist(["01_A", "02_B", "03_C"]);

        Assert.Equal(clip, playlist.Select(number));
        Assert.Equal(number, playlist.CurrentNumber);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(4)]
    [InlineData(-1)]
    public void Select_RejectsOutOfRangeAndLeavesThePlaylistAlone(int number)
    {
        var playlist = new RadioPlaylist(["01_A", "02_B", "03_C"]);
        playlist.StartAfter("01_A");

        Assert.Null(playlist.Select(number));
        Assert.Equal(1, playlist.CurrentNumber);
        Assert.Equal("02_B", playlist.Next());
    }

    [Fact]
    public void Next_AfterSelectContinuesFromTheChosenClipAndWraps()
    {
        var playlist = new RadioPlaylist(["01_A", "02_B", "03_C"]);

        playlist.Select(3);

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
