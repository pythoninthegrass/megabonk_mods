using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;

namespace MegabonkLevels;

// The lines recalled by Up/Down and the lines shown in the scrollback, oldest first.
public readonly record struct ConsoleLogSnapshot(IReadOnlyList<string> History, IReadOnlyList<string> Scrollback);

// Keeps the console's typed and printed lines across sessions as one JSON object per line; a clear marker drops the
// scrollback written before it. Persistence is best effort: an unreadable or unwritable file never reaches the game.
public sealed class ConsoleLogStore
{
    private const string InputKind = "in";
    private const string OutputKind = "out";
    private const string ClearKind = "clear";

    private readonly string _path;

    public ConsoleLogStore(string path)
    {
        _path = path;
    }

    public void AppendInput(string line) => Append(InputKind, line);

    public void AppendOutput(string line) => Append(OutputKind, line);

    public void AppendClear() => Append(ClearKind, null);

    public ConsoleLogSnapshot Load(int maxHistory, int maxScrollback)
    {
        var history = new List<string>();
        var scrollback = new List<string>();
        foreach (var line in ReadLines())
        {
            if (!TryParse(line, out var kind, out var value))
            {
                continue;
            }

            if (kind == InputKind)
            {
                history.Add(value);
            }
            else if (kind == OutputKind)
            {
                scrollback.Add(value);
            }
            else
            {
                scrollback.Clear();
            }
        }

        return new ConsoleLogSnapshot(Tail(history, maxHistory), Tail(scrollback, maxScrollback));
    }

    // Rewrites the file with just the entries Load would return, so it cannot grow without bound.
    public void Compact(int maxHistory, int maxScrollback)
    {
        if (!File.Exists(_path))
        {
            return;
        }

        var snapshot = Load(maxHistory, maxScrollback);
        var lines = new List<string>();
        foreach (var entry in snapshot.History)
        {
            lines.Add(Serialize(InputKind, entry));
        }

        foreach (var entry in snapshot.Scrollback)
        {
            lines.Add(Serialize(OutputKind, entry));
        }

        try
        {
            var temp = _path + ".tmp";
            File.WriteAllLines(temp, lines);
            File.Move(temp, _path, true);
        }
        catch (Exception)
        {
        }
    }

    private void Append(string kind, string value)
    {
        try
        {
            var directory = Path.GetDirectoryName(_path);
            if (!string.IsNullOrEmpty(directory))
            {
                Directory.CreateDirectory(directory);
            }

            File.AppendAllText(_path, Serialize(kind, value) + "\n");
        }
        catch (Exception)
        {
        }
    }

    private string[] ReadLines()
    {
        try
        {
            return File.Exists(_path) ? File.ReadAllLines(_path) : Array.Empty<string>();
        }
        catch (Exception)
        {
            return Array.Empty<string>();
        }
    }

    private static string Serialize(string kind, string value)
    {
        var entry = new Dictionary<string, string> { ["k"] = kind };
        if (value != null)
        {
            entry["v"] = value;
        }

        return JsonSerializer.Serialize(entry);
    }

    private static bool TryParse(string line, out string kind, out string value)
    {
        kind = null;
        value = null;
        if (string.IsNullOrWhiteSpace(line))
        {
            return false;
        }

        try
        {
            using var document = JsonDocument.Parse(line);
            var root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object || !root.TryGetProperty("k", out var k) || k.ValueKind != JsonValueKind.String)
            {
                return false;
            }

            kind = k.GetString();
            if (kind == ClearKind)
            {
                return true;
            }

            if (kind != InputKind && kind != OutputKind)
            {
                return false;
            }

            if (!root.TryGetProperty("v", out var v) || v.ValueKind != JsonValueKind.String)
            {
                return false;
            }

            value = v.GetString();
            return true;
        }
        catch (JsonException)
        {
            return false;
        }
    }

    private static List<string> Tail(List<string> entries, int max)
    {
        var count = Math.Max(0, max);
        return entries.Count <= count ? entries : entries.GetRange(entries.Count - count, count);
    }
}
