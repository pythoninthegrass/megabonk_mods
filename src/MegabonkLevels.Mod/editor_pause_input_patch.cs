using HarmonyLib;
using Il2Cpp;
using MelonLoader;
using UnityEngine;

namespace MegabonkLevels;

public static class EditorPauseInputPatch
{
    [HarmonyPatch(typeof(PauseUi), nameof(PauseUi.Toggle))]
    private static class TogglePrefix
    {
        private static bool Prefix()
        {
            if (!EditorTextInputPolicy.BlockGameMenu(EditorMode.Active, EditorEscapeInput.BlocksMenu))
            {
                return true;
            }

            MelonLogger.Msg("EditorTextInput: consumed game menu toggle for form Escape sequence");
            return false;
        }
    }

    [HarmonyPatch(typeof(WindowManager), nameof(WindowManager.RefreshCursor))]
    private static class RefreshCursorPrefix
    {
        private static bool Prefix()
        {
            if (!EditorMode.Active)
            {
                return true;
            }

            Cursor.lockState = CursorLockMode.None;
            Cursor.visible = true;
            return false;
        }
    }
}
