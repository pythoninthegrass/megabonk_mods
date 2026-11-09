namespace MegabonkLevels.Tests;

public class KeyRepeaterTests
{
    [Fact]
    public void Press_FiresOnceImmediately()
    {
        var repeater = new KeyRepeater(0.4f, 0.1f);

        Assert.Equal(1, repeater.Step(true, true, 0.016f));
    }

    [Fact]
    public void Hold_WaitsForTheDelayThenRepeatsAtTheInterval()
    {
        var repeater = new KeyRepeater(0.4f, 0.1f);
        repeater.Step(true, true, 0f);

        Assert.Equal(0, repeater.Step(false, true, 0.3f));
        Assert.Equal(1, repeater.Step(false, true, 0.15f));
        Assert.Equal(2, repeater.Step(false, true, 0.2f));
    }

    [Fact]
    public void Release_ResetsTheTimer()
    {
        var repeater = new KeyRepeater(0.4f, 0.1f);
        repeater.Step(true, true, 0f);
        repeater.Step(false, true, 0.39f);
        Assert.Equal(0, repeater.Step(false, false, 0.5f));

        Assert.Equal(1, repeater.Step(true, true, 0f));
        Assert.Equal(0, repeater.Step(false, true, 0.39f));
    }

    [Fact]
    public void HeldWithoutAPress_DoesNotFire()
    {
        var repeater = new KeyRepeater(0.4f, 0.1f);

        Assert.Equal(0, repeater.Step(false, false, 1f));
    }
}
