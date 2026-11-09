using System.Collections.Generic;
using UnityEngine;

namespace MegabonkLevels;

// Fades the stock HUD, including the minimap's coordinate label, without changing the coordinate preference.
public static class HudControl
{
    private static readonly HudVisibility Visibility = new();
    private static readonly Dictionary<int, HudVisibility> FollowBars = new();

    public static void Set(bool visible, ModLogger logger)
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

        SetFollowBars(visible);
        logger.Msg($"DevHarness: hud {(visible ? "shown" : "hidden")}.");
    }

    // The bar under the player is a HealthUI with followPlayer set and its own CanvasGroup, outside the HUD group.
    private static void SetFollowBars(bool visible)
    {
        foreach (var ui in Resources.FindObjectsOfTypeAll<HealthUI>())
        {
            if (!ui.followPlayer || ui.canvasGroup == null || !ui.gameObject.activeInHierarchy)
            {
                continue;
            }

            var id = ui.GetInstanceID();
            if (!FollowBars.TryGetValue(id, out var bar))
            {
                bar = FollowBars[id] = new HudVisibility();
            }

            if (visible)
            {
                if (bar.Show() is { } alpha)
                {
                    ui.canvasGroup.alpha = alpha;
                }
            }
            else
            {
                ui.canvasGroup.alpha = bar.Hide(ui.canvasGroup.alpha);
            }
        }
    }
}
