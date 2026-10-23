using System.Collections.Generic;
using System.Linq;

namespace MegabonkLevels;

// UnityEngine.KeyCode member names the harness accepts, kept Unity-free so parsing can be tested.
public static class KeyNames
{
    private static readonly string[] Named =
    {
        "UpArrow", "DownArrow", "LeftArrow", "RightArrow",
        "Escape", "Return", "Backspace", "Delete", "Space", "Tab",
        "LeftShift", "RightShift", "LeftControl", "RightControl", "LeftAlt", "RightAlt",
    };

    public static IReadOnlyList<string> All { get; } = Enumerable.Range('A', 26).Select(c => ((char)c).ToString())
        .Concat(Enumerable.Range(0, 10).Select(i => $"Alpha{i}"))
        .Concat(Enumerable.Range(0, 10).Select(i => $"Keypad{i}"))
        .Concat(Enumerable.Range(1, 12).Select(i => $"F{i}"))
        .Concat(Named)
        .ToArray();

    private static readonly HashSet<string> Valid = new(All);

    public static bool IsValid(string name) => name != null && Valid.Contains(name);
}
