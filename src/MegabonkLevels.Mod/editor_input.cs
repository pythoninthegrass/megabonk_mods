using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

// Editor input reads: the real keyboard and mouse, or the scripted state in Queue.
public static class EditorInput
{
    public static readonly InjectedInputQueue Queue = new();

    public static Vector2 MousePosition => Queue.MousePosition is var (x, y) ? new Vector2(x, y) : Input.mousePosition;

    public static string InputString => Input.inputString + Queue.InputStringThisFrame;

    public static Vector2 MouseScrollDelta => Input.mouseScrollDelta;

    public static bool GetKey(KeyCode key) => Input.GetKey(key) || Queue.IsKeyHeld(key.ToString());

    public static bool GetKeyDown(KeyCode key) => Input.GetKeyDown(key) || Queue.WasKeyPressedThisFrame(key.ToString());

    public static bool GetKeyUp(KeyCode key) => Input.GetKeyUp(key) || Queue.WasKeyReleasedThisFrame(key.ToString());

    public static bool GetMouseButton(int button) => Input.GetMouseButton(button) || Queue.IsMouseHeld(button);

    public static bool GetMouseButtonDown(int button) => Input.GetMouseButtonDown(button) || Queue.WasMousePressedThisFrame(button);

    public static bool GetMouseButtonUp(int button) => Input.GetMouseButtonUp(button) || Queue.WasMouseReleasedThisFrame(button);

    public static float GetAxisRaw(string axis) => Input.GetAxisRaw(axis);

    // Logs the real keyboard only, bypassing Queue, so a keypress that the game never receives shows up as a missing line.
    public static void LogRealTextInput(MelonLogger.Instance logger, bool fieldFocused)
    {
        var line = RealInputDiagnostic.Describe(
            Input.inputString,
            Input.GetKeyDown(KeyCode.Backspace),
            Input.GetKeyDown(KeyCode.Return) || Input.GetKeyDown(KeyCode.KeypadEnter),
            fieldFocused);
        if (line != null)
        {
            logger.Msg(line);
        }
    }
}
