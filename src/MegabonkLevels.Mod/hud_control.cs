using Il2Cpp;
using MelonLoader;

namespace MegabonkLevels;

// Dev-harness switch that fades the stock HUD group (the position readout sits under the minimap) for clean captures.
public static class HudControl
{
    private static readonly HudVisibility Visibility = new();

    public static void Set(bool visible, MelonLogger.Instance logger)
    {
        var group = UiManager.Instance?.hudGroup;
        if (group == null)
        {
            logger.Warning("DevHarness: hud ignored, no HUD group in the scene.");
            return;
        }

        if (visible)
        {
            if (Visibility.Show() is { } alpha)
            {
                group.alpha = alpha;
            }
        }
        else
        {
            group.alpha = Visibility.Hide(group.alpha);
        }

        logger.Msg($"DevHarness: hud {(visible ? "shown" : "hidden")}.");
    }
}
