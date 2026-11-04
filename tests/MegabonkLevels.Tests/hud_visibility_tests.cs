namespace MegabonkLevels.Tests;

public class HudVisibilityTests
{
    [Fact]
    public void Hide_ReturnsZeroAlphaAndMarksTheHudHidden()
    {
        var hud = new HudVisibility();

        Assert.Equal(0f, hud.Hide(1f));
        Assert.True(hud.Hidden);
    }

    [Fact]
    public void Show_RestoresTheAlphaSeenAtTheFirstHide()
    {
        var hud = new HudVisibility();
        hud.Hide(0.6f);

        Assert.Equal(0.6f, hud.Show());
        Assert.False(hud.Hidden);
    }

    [Fact]
    public void Hide_WhileAlreadyHidden_KeepsTheOriginalAlpha()
    {
        var hud = new HudVisibility();
        hud.Hide(0.6f);
        hud.Hide(0f);

        Assert.Equal(0.6f, hud.Show());
    }

    [Fact]
    public void Show_WithNothingSaved_ReturnsNull()
    {
        Assert.Null(new HudVisibility().Show());
    }

    [Fact]
    public void Show_TwiceInARow_RestoresOnlyOnce()
    {
        var hud = new HudVisibility();
        hud.Hide(1f);
        hud.Show();

        Assert.Null(hud.Show());
    }

    [Fact]
    public void Show_AfterHidingAnAlreadyInvisibleHud_RestoresZero()
    {
        var hud = new HudVisibility();
        hud.Hide(0f);

        Assert.Equal(0f, hud.Show());
    }
}
