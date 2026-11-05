namespace MegabonkLevels;

// Decides whether a death-screen button press may proceed; the error names the first thing that is missing.
public static class DeathScreenPressGate
{
    public const string Confirm = "confirm";
    public const string SummaryRestart = "summary-restart";

    public static string Refusal(string press, bool screenShowing, bool windowShowing, bool buttonActive, bool buttonInteractable)
    {
        var confirm = press == Confirm;
        if (!screenShowing)
        {
            return "no death screen is showing";
        }

        if (!windowShowing)
        {
            return confirm ? "the death screen's Confirm is not showing" : "the run summary is not showing";
        }

        var button = confirm ? "the death screen's Confirm button" : "the run summary's Restart button";
        if (!buttonActive)
        {
            return $"{button} is not active";
        }

        return buttonInteractable ? null : $"{button} is not interactable";
    }
}
