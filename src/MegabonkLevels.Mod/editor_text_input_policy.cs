namespace MegabonkLevels;

public static class EditorTextInputPolicy
{
    public static bool BlockGameMenu(bool editorActive, bool textInputCaptured) => editorActive && textInputCaptured;
}
