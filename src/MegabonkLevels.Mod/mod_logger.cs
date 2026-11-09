using BepInEx.Logging;

namespace MegabonkLevels;

public sealed class ModLogger
{
    private readonly ManualLogSource _source;

    public ModLogger(ManualLogSource source) => _source = source;

    internal static ModLogger Default { get; set; }

    public void Msg(string message) => _source.LogInfo(message);
    public void Warning(string message) => _source.LogWarning(message);
    public void Error(string message) => _source.LogError(message);
}
