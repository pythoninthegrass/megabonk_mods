using System.IO;

namespace MegabonkLevels;

public sealed class ModContentPaths
{
    public ModContentPaths(string gameRoot, string pluginDirectory)
    {
        GameRoot = gameRoot;
        PluginDirectory = pluginDirectory;
    }

    public string GameRoot { get; }
    public string PluginDirectory { get; }
    public string UserData => Path.Combine(GameRoot, "UserData");
    public string Harness => Path.Combine(GameRoot, "harness");
    public string TestLevel => Path.Combine(PluginDirectory, "megabonklevels-test-level.mblevel.json");
}
