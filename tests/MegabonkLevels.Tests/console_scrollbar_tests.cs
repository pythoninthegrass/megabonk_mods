namespace MegabonkLevels.Tests;

public class ConsoleScrollbarTests
{
    [Fact]
    public void Visible_IsFalseAtRest()
    {
        var bar = new ConsoleScrollbar();

        Assert.False(bar.Visible(0.0, 100, 10));
    }

    [Fact]
    public void Visible_IsTrueAfterAWheelEvent()
    {
        var bar = new ConsoleScrollbar();
        bar.OnWheel(5.0);

        Assert.True(bar.Visible(5.0, 100, 10));
        Assert.True(bar.Visible(6.9, 100, 10));
    }

    [Fact]
    public void Visible_HidesTwoSecondsAfterTheLastWheelEvent()
    {
        var bar = new ConsoleScrollbar();
        bar.OnWheel(5.0);

        Assert.False(bar.Visible(7.0, 100, 10));
    }

    [Fact]
    public void OnWheel_RestartsTheTimer()
    {
        var bar = new ConsoleScrollbar();
        bar.OnWheel(5.0);
        bar.OnWheel(6.5);

        Assert.True(bar.Visible(8.4, 100, 10));
        Assert.False(bar.Visible(8.5, 100, 10));
    }

    [Fact]
    public void Visible_IsFalseWhenTheScrollbackFitsOnScreen()
    {
        var bar = new ConsoleScrollbar();
        bar.OnWheel(5.0);

        Assert.False(bar.Visible(5.0, 10, 10));
        Assert.False(bar.Visible(5.0, 3, 10));
    }

    [Fact]
    public void Hide_ClearsAVisibleBar()
    {
        var bar = new ConsoleScrollbar();
        bar.OnWheel(5.0);
        bar.Hide();

        Assert.False(bar.Visible(5.0, 100, 10));
    }

    [Fact]
    public void Thumb_AtTheBottom_SitsAtTheEndOfTheTrack()
    {
        var thumb = ConsoleScrollbar.Thumb(offset: 0, count: 100, viewport: 10, track: 200f, minHeight: 12f);

        Assert.Equal(20f, thumb.Height, 3);
        Assert.Equal(180f, thumb.Top, 3);
    }

    [Fact]
    public void Thumb_AtTheTop_SitsAtTheStartOfTheTrack()
    {
        var thumb = ConsoleScrollbar.Thumb(offset: 90, count: 100, viewport: 10, track: 200f, minHeight: 12f);

        Assert.Equal(20f, thumb.Height, 3);
        Assert.Equal(0f, thumb.Top, 3);
    }

    [Fact]
    public void Thumb_Midway_SitsMidway()
    {
        var thumb = ConsoleScrollbar.Thumb(offset: 45, count: 100, viewport: 10, track: 200f, minHeight: 12f);

        Assert.Equal(90f, thumb.Top, 3);
    }

    [Fact]
    public void Thumb_NeverShrinksBelowTheMinimumHeight()
    {
        var thumb = ConsoleScrollbar.Thumb(offset: 0, count: 400, viewport: 5, track: 200f, minHeight: 12f);

        Assert.Equal(12f, thumb.Height, 3);
        Assert.Equal(188f, thumb.Top, 3);
    }

    [Fact]
    public void Thumb_WhenEverythingFits_FillsTheTrack()
    {
        var thumb = ConsoleScrollbar.Thumb(offset: 0, count: 4, viewport: 10, track: 200f, minHeight: 12f);

        Assert.Equal(200f, thumb.Height, 3);
        Assert.Equal(0f, thumb.Top, 3);
    }
}
