namespace MegabonkLevels.Tests;

public class EditorReenterPolicyTests
{
    [Fact]
    public void ShouldEnter_WhenRequestedAndReady_ReturnsTrue()
    {
        Assert.True(EditorReenterPolicy.ShouldEnter(requested: true, active: false, runInProgress: true, consoleOpen: false));
    }

    [Theory]
    [InlineData(false, false, true, false)]
    [InlineData(true, true, true, false)]
    [InlineData(true, false, false, false)]
    [InlineData(true, false, true, true)]
    public void ShouldEnter_WhenBlocked_ReturnsFalse(bool requested, bool active, bool runInProgress, bool consoleOpen)
    {
        Assert.False(EditorReenterPolicy.ShouldEnter(requested, active, runInProgress, consoleOpen));
    }
}
