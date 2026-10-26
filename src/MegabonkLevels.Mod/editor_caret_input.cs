using UnityEngine;

namespace MegabonkLevels;

// Reads caret keys through EditorInput so injected keys work too; arrows and Delete repeat while held.
public sealed class EditorCaretInput
{
    private readonly KeyRepeater _left = new();
    private readonly KeyRepeater _right = new();
    private readonly KeyRepeater _delete = new();

    public CaretKeys Read()
    {
        var dt = Time.unscaledDeltaTime;
        return new CaretKeys(
            Left: Repeat(_left, KeyCode.LeftArrow, dt),
            Right: Repeat(_right, KeyCode.RightArrow, dt),
            Delete: Repeat(_delete, KeyCode.Delete, dt),
            Home: EditorInput.GetKeyDown(KeyCode.Home),
            End: EditorInput.GetKeyDown(KeyCode.End));
    }

    private static int Repeat(KeyRepeater repeater, KeyCode key, float dt) =>
        repeater.Step(EditorInput.GetKeyDown(key), EditorInput.GetKey(key), dt);
}
