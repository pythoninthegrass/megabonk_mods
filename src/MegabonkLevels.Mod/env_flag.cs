using System;

namespace MegabonkLevels;

// Opt-in switches for development diagnostics, read from the game process's environment.
public static class EnvFlag
{
    public static bool IsEnabled(string value)
    {
        var trimmed = value?.Trim();
        return trimmed == "1" || string.Equals(trimmed, "true", StringComparison.OrdinalIgnoreCase);
    }

    public static bool IsSet(string variable) => IsEnabled(Environment.GetEnvironmentVariable(variable));
}
