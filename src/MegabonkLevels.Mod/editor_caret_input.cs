using UnityEngine;

namespace MegabonkLevels;

// Reads caret keys through EditorInput so injected keys work too; arrows and Delete repeat while held.
public sealed class EditorCaretInput
{
    private readonly KeyRepeater _left = new();
    private readonly KeyRepeater _right = new();
    private readonly KeyRepeater _delete = new();

    // Option (Alt) with an arrow jumps a word instead of a character.
    public CaretKeys Read()
    {
        var dt = Time.unscaledDeltaTime;
        var word = EditorInput.GetKey(KeyCode.LeftAlt) || EditorInput.GetKey(KeyCode.RightAlt);
        var left = Repeat(_left, KeyCode.LeftArrow, dt);
        var right = Repeat(_right, KeyCode.RightArrow, dt);
        return new CaretKeys(
            Left: word ? 0 : left,
            Right: word ? 0 : right,
            Delete: Repeat(_delete, KeyCode.Delete, dt),
            Home: EditorInput.GetKeyDown(KeyCode.Home),
            End: EditorInput.GetKeyDown(KeyCode.End),
            WordLeft: word ? left : 0,
            WordRight: word ? right : 0);
    }

    private static int Repeat(KeyRepeater repeater, KeyCode key, float dt) =>
        repeater.Step(EditorInput.GetKeyDown(key), EditorInput.GetKey(key), dt);
}
