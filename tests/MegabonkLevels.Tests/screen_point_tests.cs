namespace MegabonkLevels.Tests;

public class ScreenPointTests
{
    [Fact]
    public void ToUnity_FlipsTheVerticalAxisAgainstTheScreenHeight()
    {
        Assert.Equal((960f, 1080f), ScreenPoint.ToUnity(960f, 0f, 1080));
        Assert.Equal((0f, 0f), ScreenPoint.ToUnity(0f, 1080f, 1080));
        Assert.Equal((100f, 540f), ScreenPoint.ToUnity(100f, 540f, 1080));
    }

    [Fact]
    public void ToUnity_KeepsFractionalPixels()
    {
        Assert.Equal((10.5f, 79.75f), ScreenPoint.ToUnity(10.5f, 20.25f, 100));
    }
}
