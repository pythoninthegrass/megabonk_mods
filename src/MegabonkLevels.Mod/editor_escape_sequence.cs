namespace MegabonkLevels;

public enum EditorTextField { None, Search, Save }

public enum EditorEscapeAction { GameMenu, Blur, Clear }

public readonly record struct EditorEscapeResult(EditorEscapeAction Action, EditorTextField Field);

public sealed class EditorEscapeSequence
{
    private EditorTextField _pendingClear;
    private int _consumedFrame = -1;

    public bool CapturedInFrame(int frame) => _consumedFrame == frame;

    public bool BlocksMenu(EditorTextField focused, int frame, bool searchHasText = true, bool saveHasText = true) =>
        CapturedInFrame(frame) || HasText(TargetField(focused), searchHasText, saveHasText);

    public EditorEscapeResult Press(EditorTextField focused, int frame, bool searchHasText = true, bool saveHasText = true)
    {
        var target = TargetField(focused);
        if (!HasText(target, searchHasText, saveHasText))
        {
            _pendingClear = EditorTextField.None;
            return new(EditorEscapeAction.GameMenu, target);
        }

        if (focused != EditorTextField.None)
        {
            _pendingClear = focused;
            _consumedFrame = frame;
            return new(EditorEscapeAction.Blur, focused);
        }

        if (_pendingClear != EditorTextField.None)
        {
            var field = _pendingClear;
            _pendingClear = EditorTextField.None;
            _consumedFrame = frame;
            return new(EditorEscapeAction.Clear, field);
        }

        return new(EditorEscapeAction.GameMenu, EditorTextField.None);
    }

    private EditorTextField TargetField(EditorTextField focused) => focused != EditorTextField.None ? focused : _pendingClear;

    private static bool HasText(EditorTextField field, bool searchHasText, bool saveHasText) => field switch
    {
        EditorTextField.Search => searchHasText,
        EditorTextField.Save => saveHasText,
        _ => false,
    };

    public void Reset()
    {
        _pendingClear = EditorTextField.None;
        _consumedFrame = -1;
    }
}
