using System;
using Il2CppRewired;
using MelonLoader;

namespace MegabonkLevels;

// Reads the game's slide button through Rewired. The harness injects only editor input, never Rewired input,
// so an override stands in for the keyboard while the grind gate is checked in game.
public static class GrindInput
{
    private static MelonLogger.Instance _logger;
    private static bool? _forced;
    private static Player _player;
    private static bool _failureReported;

    public static void Install(MelonLogger.Instance logger)
    {
        _logger = logger;
    }

    // true holds the button down, false releases it, null hands the read back to the real device.
    public static void Force(bool? held, MelonLogger.Instance logger = null)
    {
        _forced = held;
        (logger ?? _logger)?.Msg($"GrindInput: slide button {(held == null ? "back on the real device" : held.Value ? "held" : "released")}.");
    }

    // The override the harness set, or null while the real device is read.
    public static bool? Forced => _forced;

    public static bool IsSlideHeld()
    {
        if (_forced.HasValue)
        {
            return _forced.Value;
        }

        try
        {
            _player ??= ReInput.players.GetPlayer(0);
            return _player != null && _player.GetButton(GrindGate.SlideAction);
        }
        catch (Exception ex)
        {
            _player = null;
            ReportFailure(ex);
            return GrindGate.SlideHeldWhenReadFails;
        }
    }

    // Logged once. An unknown action name reads as held forever, so the mapping is asked whether the action exists at all.
    private static void ReportFailure(Exception ex)
    {
        if (_failureReported)
        {
            return;
        }

        _failureReported = true;
        var actionId = ActionId();
        _logger?.Warning($"GrindInput: reading the '{GrindGate.SlideAction}' action failed ({ex.GetType().Name}: {ex.Message}); grind starts stay allowed. Action id: {(actionId < 0 ? "not in the mapping" : actionId.ToString())}.");
    }

    // The mapping's id for the slide action, or -1 when the game has no action by that name.
    private static int ActionId()
    {
        try
        {
            return ReInput.mapping.GetActionId(GrindGate.SlideAction);
        }
        catch (Exception ex)
        {
            _logger?.Warning($"GrindInput: the mapping could not be read either ({ex.GetType().Name}: {ex.Message}).");
            return -1;
        }
    }
}
