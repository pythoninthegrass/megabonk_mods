using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace MegabonkLevels;

// Maps UnityEngine.KeyCode names to the text a US keyboard types, for runtimes that deliver key state but no Input.inputString.
public static class KeyTextMapper
{
    private static readonly Dictionary<string, (char Plain, char Shifted)> Table = BuildTable();

    public static IReadOnlyList<string> Keys { get; } = Table.Keys.ToArray();

    public static char? CharFor(string keyName, bool shift) =>
        keyName != null && Table.TryGetValue(keyName, out var chars) ? (shift ? chars.Shifted : chars.Plain) : null;

    public static string TextFor(IEnumerable<string> keyNames, bool shift)
    {
        var text = new StringBuilder();
        foreach (var name in keyNames)
        {
            if (CharFor(name, shift) is { } c)
            {
                text.Append(c);
            }
        }

        return text.ToString();
    }

    private static Dictionary<string, (char, char)> BuildTable()
    {
        var table = new Dictionary<string, (char, char)>();
        for (var c = 'A'; c <= 'Z'; c++)
        {
            table[c.ToString()] = (char.ToLowerInvariant(c), c);
        }

        const string shiftedDigits = ")!@#$%^&*(";
        for (var i = 0; i <= 9; i++)
        {
            table[$"Alpha{i}"] = ((char)('0' + i), shiftedDigits[i]);
            table[$"Keypad{i}"] = ((char)('0' + i), (char)('0' + i));
        }

        table["Minus"] = ('-', '_');
        table["Equals"] = ('=', '+');
        table["LeftBracket"] = ('[', '{');
        table["RightBracket"] = (']', '}');
        table["Semicolon"] = (';', ':');
        table["Quote"] = ('\'', '"');
        table["Comma"] = (',', '<');
        table["Period"] = ('.', '>');
        table["Slash"] = ('/', '?');
        table["Backslash"] = ('\\', '|');
        table["BackQuote"] = ('`', '~');
        table["Space"] = (' ', ' ');
        table["KeypadPeriod"] = ('.', '.');
        table["KeypadMinus"] = ('-', '-');
        table["KeypadPlus"] = ('+', '+');
        table["KeypadMultiply"] = ('*', '*');
        table["KeypadDivide"] = ('/', '/');
        table["Backspace"] = ('\b', '\b');
        table["Return"] = ('\n', '\n');
        table["KeypadEnter"] = ('\n', '\n');
        return table;
    }
}
