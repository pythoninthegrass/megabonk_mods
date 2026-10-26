using UnityEngine;

namespace MegabonkLevels;

public static class EditorEscapeInput
{
    private static readonly EditorEscapeSequence _sequence = new();

    private static EditorTextField FocusedField => EditorPalette.SearchFocused ? EditorTextField.Search
        : EditorTileTools.SaveInputFocused ? EditorTextField.Save : EditorTextField.None;

    public static bool BlocksMenu => _sequence.BlocksMenu(FocusedField, Time.frameCount, EditorPalette.SearchHasText, EditorTileTools.SaveInputHasText);

    public static bool CapturedThisFrame => _sequence.CapturedInFrame(Time.frameCount);

    public static void Reset() => _sequence.Reset();

    public static void Tick()
    {
        if (!EditorInput.GetKeyDown(KeyCode.Escape))
        {
            return;
        }

        var result = _sequence.Press(FocusedField, Time.frameCount, EditorPalette.SearchHasText, EditorTileTools.SaveInputHasText);
        if (result.Field == EditorTextField.Search)
        {
            EditorPalette.BlurSearch();
            if (result.Action == EditorEscapeAction.Clear)
            {
                EditorPalette.ClearSearch();
            }
        }
        else if (result.Field == EditorTextField.Save)
        {
            EditorTileTools.BlurSaveInput();
            if (result.Action == EditorEscapeAction.Clear)
            {
                EditorTileTools.ClearSaveInput();
            }
        }
    }
}
