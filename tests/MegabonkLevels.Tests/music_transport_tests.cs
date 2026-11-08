namespace MegabonkLevels.Tests;

public class MusicTransportTests
{
    [Fact]
    public void List_NumbersTheTracksFromOneAndMarksTheCurrentOne()
    {
        var text = MusicTransportReply.List(["01_A", "02_B", "03_C"], 2);

        Assert.Equal("   1  01_A\n > 2  02_B\n   3  03_C", text);
    }

    [Fact]
    public void List_WithNoCurrentTrackMarksNone()
    {
        Assert.DoesNotContain(">", MusicTransportReply.List(["01_A", "02_B"], 0));
    }

    [Fact]
    public void Now_NamesTheTrackAndItsPlaceInTheList()
    {
        Assert.Equal("2/3  02_B", MusicTransportReply.Now(["01_A", "02_B", "03_C"], 2));
    }

    [Fact]
    public void Now_WithNoCurrentTrackSaysSo()
    {
        Assert.Equal("no track chosen yet", MusicTransportReply.Now(["01_A"], 0));
    }

    [Fact]
    public void Changed_NamesTheNewTrackAndItsNumber()
    {
        Assert.Equal("playing 3/3  03_C", MusicTransportReply.Changed(["01_A", "02_B", "03_C"], 3));
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
}
