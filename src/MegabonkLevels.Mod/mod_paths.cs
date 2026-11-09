using System.IO;
using BepInEx;

namespace MegabonkLevels;

internal static class ModPaths
{
    private static readonly ModContentPaths Content = new(Paths.GameRootPath,
        Path.GetDirectoryName(typeof(MegabonkLevelsMod).Assembly.Location));

    public static string GameRootDirectory => Content.GameRoot;
    public static string UserDataDirectory => Content.UserData;
    public static string HarnessDirectory => Content.Harness;
    public static string TestLevel => Content.TestLevel;
}
