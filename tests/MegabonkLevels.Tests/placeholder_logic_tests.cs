namespace MegabonkLevels.Tests;

public class PlaceholderLogicTests
{
    [Fact]
    public void AddOne_ReturnsIncrementedValue()
    {
        Assert.Equal(2, PlaceholderLogic.AddOne(1));
    }
}
