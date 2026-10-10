namespace MegabonkLevels.Tests;

public class PaletteScrollTests
{
    [Fact]
    public void OffsetToReveal_RowAlreadyVisible_KeepsTheOffset()
    {
        Assert.Equal(100f, PaletteScroll.OffsetToReveal(150f, 26f, 400f, 100f, 2000f));
    }

    [Fact]
    public void OffsetToReveal_RowBelowTheView_CentresIt()
    {
        Assert.Equal(1000f - 200f + 13f, PaletteScroll.OffsetToReveal(1000f, 26f, 400f, 0f, 2000f));
    }

    [Fact]
    public void OffsetToReveal_RowAboveTheView_CentresIt()
    {
        Assert.Equal(500f - 200f + 13f, PaletteScroll.OffsetToReveal(500f, 26f, 400f, 1200f, 2000f));
    }

    [Fact]
    public void OffsetToReveal_RowNearTheTop_ClampsToZero()
    {
        Assert.Equal(0f, PaletteScroll.OffsetToReveal(50f, 26f, 400f, 900f, 2000f));
    }

    [Fact]
    public void OffsetToReveal_RowNearTheBottom_ClampsToTheLastPage()
    {
        Assert.Equal(1600f, PaletteScroll.OffsetToReveal(1990f, 26f, 400f, 0f, 2000f));
    }

    [Fact]
    public void OffsetToReveal_ContentShorterThanTheView_IsZero()
    {
        Assert.Equal(0f, PaletteScroll.OffsetToReveal(300f, 26f, 400f, 0f, 350f));
    }
}
