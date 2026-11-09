namespace MegabonkLevels.Tests;

public class DeathScreenPressGateTests
{
    [Fact]
    public void Refusal_AllowsAShowingScreenWithAnInteractableButton()
    {
        Assert.Null(DeathScreenPressGate.Refusal(DeathScreenPressGate.Confirm, true, true, true, true));
        Assert.Null(DeathScreenPressGate.Refusal(DeathScreenPressGate.SummaryRestart, true, true, true, true));
    }

    [Fact]
    public void Refusal_NamesTheMissingDeathScreen()
    {
        var error = DeathScreenPressGate.Refusal(DeathScreenPressGate.Confirm, false, false, false, false);

        Assert.Equal("no death screen is showing", error);
    }

    [Theory]
    [InlineData(DeathScreenPressGate.Confirm, "the death screen's Confirm is not showing")]
    [InlineData(DeathScreenPressGate.SummaryRestart, "the run summary is not showing")]
    public void Refusal_NamesTheWindowThatIsNotShowing(string press, string expected)
    {
        Assert.Equal(expected, DeathScreenPressGate.Refusal(press, true, false, true, true));
    }

    [Theory]
    [InlineData(DeathScreenPressGate.Confirm, "the death screen's Confirm button is not active")]
    [InlineData(DeathScreenPressGate.SummaryRestart, "the run summary's Restart button is not active")]
    public void Refusal_NamesAnInactiveButton(string press, string expected)
    {
        Assert.Equal(expected, DeathScreenPressGate.Refusal(press, true, true, false, true));
    }

    [Theory]
    [InlineData(DeathScreenPressGate.Confirm, "the death screen's Confirm button is not interactable")]
    [InlineData(DeathScreenPressGate.SummaryRestart, "the run summary's Restart button is not interactable")]
    public void Refusal_RefusesANonInteractableButton(string press, string expected)
    {
        Assert.Equal(expected, DeathScreenPressGate.Refusal(press, true, true, true, false));
    }
}
