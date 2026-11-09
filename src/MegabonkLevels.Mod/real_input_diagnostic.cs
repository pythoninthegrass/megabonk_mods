using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace MegabonkLevels;

// Formats one frame of real keyboard text input for the log; the injected queue never feeds it.
public static class RealInputDiagnostic
{
    public static string Describe(string inputString, bool backspaceDown, bool returnDown, bool fieldFocused)
    {
        var parts = new List<string>();
        if (!string.IsNullOrEmpty(inputString))
        {
            parts.Add($"inputString=\"{Escape(inputString)}\" codes={string.Join(" ", inputString.Select(c => (int)c))}");
        }

        if (backspaceDown)
        {
            parts.Add("Backspace down");
        }

        if (returnDown)
        {
            parts.Add("Return down");
        }

        return parts.Count == 0 ? null : $"RealInput: {string.Join(", ", parts)}, focused={(fieldFocused ? "true" : "false")}";
    }

    private static string Escape(string text)
    {
        var escaped = new StringBuilder();
        foreach (var c in text)
        {
            escaped.Append(c switch
            {
                '\b' => "\\b",
                '\r' => "\\r",
                '\n' => "\\n",
                '"' => "\\\"",
                '\\' => "\\\\",
                _ when char.IsControl(c) => $"\\x{(int)c:x2}",
                _ => c.ToString(),
            });
        }

        return escaped.ToString();
    }
}
