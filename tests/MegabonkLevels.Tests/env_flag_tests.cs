namespace MegabonkLevels.Tests;

public class EnvFlagTests
{
    [Theory]
    [InlineData("1")]
    [InlineData("true")]
    [InlineData("TRUE")]
    [InlineData("True")]
    [InlineData(" 1 ")]
    public void IsEnabled_TruthyValues_AreEnabled(string value)
    {
        Assert.True(EnvFlag.IsEnabled(value));
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("0")]
    [InlineData("false")]
    [InlineData("yes")]
    public void IsEnabled_UnsetEmptyOrOtherValues_AreDisabled(string value)
    {
        Assert.False(EnvFlag.IsEnabled(value));
    }
}
