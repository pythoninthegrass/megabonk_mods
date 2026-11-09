using System.Collections.Generic;

namespace MegabonkLevels;

// Tab state for the input line: a Tab on the line the last Tab wrote steps to the next match, any other line completes afresh.
public sealed class ConsoleCompleter
{
    private readonly ConsoleCommandRegistry _registry;

    private ConsoleCompletion _completion;

    private string _written;

    public ConsoleCompleter(ConsoleCommandRegistry registry)
    {
        _registry = registry;
    }

    // The line to show after Tab, or null when nothing completes and the line stays as typed.
    public string Tab(string line, int caret, IReadOnlyList<string> levels)
    {
        var completion = _written != null && line == _written
            ? _completion.Next()
            : _registry.Complete(line.Substring(0, caret), levels);
        if (completion.Matches.Count == 0)
        {
            return null;
        }

        _completion = completion;
        _written = completion.Line + " ";
        return _written;
    }
}
