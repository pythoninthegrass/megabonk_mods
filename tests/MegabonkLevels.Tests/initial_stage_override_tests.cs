namespace MegabonkLevels.Tests;

public class InitialStageOverrideTests
{
    [Theory]
    [InlineData(false, false)]
    [InlineData(false, true)]
    [InlineData(true, false)]
    public void RequiresBothDevelopmentAndExplicitOptIn(bool development, bool enabled)
    {
        var selection = new InitialStageOverride();
        selection.Arm(1, development, enabled);
        Assert.Null(selection.TakeBeforeAdvance(-1));
    }

    [Theory]
    [InlineData(0, -1)]
    [InlineData(1, 0)]
    [InlineData(2, 1)]
    public void SetsIndexBeforeVanillaIncrementOnce(int requested, int previous)
    {
        var selection = new InitialStageOverride();
        selection.Arm(requested, true, true);
        Assert.Equal(previous, selection.TakeBeforeAdvance(-1));
        Assert.Null(selection.TakeBeforeAdvance(-1));
    }

    [Fact]
    public void DoesNotRedirectLaterStageAdvances()
    {
        var selection = new InitialStageOverride();
        selection.Arm(1, true, true);
        Assert.Null(selection.TakeBeforeAdvance(0));
        Assert.Null(selection.TakeBeforeAdvance(-1));
    }

    [Fact]
    public void DisabledLoadClearsAnEarlierRequest()
    {
        var selection = new InitialStageOverride();
        selection.Arm(2, true, true);
        selection.Arm(1, true, false);
        Assert.Null(selection.TakeBeforeAdvance(-1));
    }
}
