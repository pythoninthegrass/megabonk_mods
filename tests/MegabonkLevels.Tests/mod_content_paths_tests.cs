namespace MegabonkLevels.Tests;

public class ModContentPathsTests
{
    [Fact]
    public void ContentStaysInGameUserDataWhileTestLevelLivesBesidePlugin()
    {
        var game = Path.Combine(Path.GetTempPath(), "game");
        var plugin = Path.Combine(game, "BepInEx", "plugins", "MegabonkLevels");
        var paths = new ModContentPaths(game, plugin);

        Assert.Equal(Path.Combine(game, "UserData"), paths.UserData);
        Assert.Equal(Path.Combine(game, "harness"), paths.Harness);
        Assert.Equal(Path.Combine(plugin, "megabonklevels-test-level.mblevel.json"), paths.TestLevel);
    }
}
