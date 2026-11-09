using System;
using System.Linq;
using System.Text.Json.Nodes;
using Il2CppInterop.Runtime;
using TMPro;
using UnityEngine;
using UnityEngine.UI;

namespace MegabonkLevels;

// Presses the death screen's Confirm and the run summary's Restart through the buttons' own onClick; see docs/development.md.
public static class DeathScreenPress
{
    private static ModLogger _logger;

    public static void Install(ModLogger logger)
    {
        _logger = logger;
    }

    // Confirm is the DeathScreen's own B_Continue; the "you ded" window (deadUiWindow) holds only the text.
    public static JsonObject PressConfirm()
    {
        var screen = ActiveDeathScreen();
        var button = screen?.b_continue == null ? null : screen.b_continue.GetComponent<Button>();
        var windowShowing = screen != null && !StatsShowing(screen);
        return Press(DeathScreenPressGate.Confirm, screen, windowShowing, button);
    }

    // The summary's Restart is DeathScreen.restartBtn, the object named B_Retry.
    public static JsonObject PressSummaryRestart()
    {
        var screen = ActiveDeathScreen();
        var button = screen?.restartBtn == null ? null : screen.restartBtn.GetComponent<Button>();
        return Press(DeathScreenPressGate.SummaryRestart, screen, screen != null && StatsShowing(screen), button);
    }

    private static bool StatsShowing(DeathScreen screen) => screen.statsWindow != null && screen.statsWindow.activeInHierarchy;

    private static DeathScreen ActiveDeathScreen()
    {
        foreach (var found in Resources.FindObjectsOfTypeAll(Il2CppType.From(typeof(DeathScreen))))
        {
            var screen = found?.TryCast<DeathScreen>();
            if (screen != null && screen.gameObject.activeInHierarchy)
            {
                return screen;
            }
        }

        return null;
    }

    private static JsonObject Press(string press, DeathScreen screen, bool windowShowing, Button button)
    {
        var refusal = DeathScreenPressGate.Refusal(
            press,
            screen != null,
            windowShowing,
            button != null && button.gameObject.activeInHierarchy,
            button != null && button.interactable);
        if (refusal != null)
        {
            _logger.Msg($"DeathScreenPress: {press} refused: {refusal}.");
            throw new InvalidOperationException(refusal);
        }

        var name = button.gameObject.name;
        var label = string.Join(" ", button.GetComponentsInChildren<TextMeshProUGUI>(false).Select(t => t.text));
        button.onClick.Invoke();
        _logger.Msg($"DeathScreenPress: {press} pressed '{name}' (label '{label}').");
        return new JsonObject { ["screenWasOpen"] = true, ["button"] = name, ["label"] = label };
    }
}
