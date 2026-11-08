namespace MegabonkLevels.Tests;

public class MusicTransportTests
{
    [Fact]
    public void List_NumbersTheTracksFromOneAndMarksTheCurrentOne()
    {
        var text = MusicTransportReply.List(["01_A", "02_B", "03_C"], 2);

        Assert.Equal("   1  A\n > 2  B\n   3  C", text);
    }

    [Fact]
    public void List_WithNoCurrentTrackMarksNone()
    {
        Assert.DoesNotContain(">", MusicTransportReply.List(["01_A", "02_B"], 0));
    }

    [Fact]
    public void Now_NamesTheTrackAndItsPlaceInTheList()
    {
        Assert.Equal("2/3  B", MusicTransportReply.Now(["01_A", "02_B", "03_C"], 2));
    }

    [Fact]
    public void Now_WithNoCurrentTrackSaysSo()
    {
        Assert.Equal("no track chosen yet", MusicTransportReply.Now(["01_A"], 0));
    }

    [Fact]
    public void Changed_NamesTheNewTrackAndItsNumber()
    {
        Assert.Equal("playing 3/3  C", MusicTransportReply.Changed(["01_A", "02_B", "03_C"], 3));
    }

    [Fact]
    public void NoPlaylist_IsTheFixedStockStageReply()
    {
        Assert.Equal("no custom playlist on this stage", MusicTransportReply.NoPlaylist);
    }

    [Fact]
    public void OutOfRange_NamesTheValidRange()
    {
        Assert.Equal("track 9 is not between 1 and 3", MusicTransportReply.OutOfRange(9, 3));
    }

    [Theory]
    [InlineData("37_The_Tourist", "The_Tourist")]
    [InlineData("06_01_Screamer", "Screamer")]
    [InlineData("06_02_Nothing_To_Me", "Nothing_To_Me")]
    [InlineData("06.01 Screamer", "Screamer")]
    [InlineData("14 Strobe", "Strobe")]
    [InlineData("12Xu", "12Xu")]
    [InlineData("27_12Xu", "12Xu")]
    [InlineData("Intro", "Intro")]
    [InlineData("07", "07")]
    [InlineData("07_", "07_")]
    public void DisplayName_DropsTheLeadingFileNumber(string name, string expected)
    {
        Assert.Equal(expected, MusicTransportReply.DisplayName(name));
    }

    [Fact]
    public void ListNowAndChanged_ShowNamesWithoutTheFileNumber()
    {
        var names = new[] { "06_01_Screamer", "37_The_Tourist" };

        Assert.Equal("   1  Screamer\n > 2  The_Tourist", MusicTransportReply.List(names, 2));
        Assert.Equal("2/2  The_Tourist", MusicTransportReply.Now(names, 2));
        Assert.Equal("playing 2/2  The_Tourist", MusicTransportReply.Changed(names, 2));
    }
}
