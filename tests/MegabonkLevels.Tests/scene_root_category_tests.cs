namespace MegabonkLevels.Tests;

public class SceneRootCategoryTests
{
    [Theory]
    [InlineData("Tree0(Clone)", "object:Tree0")]
    [InlineData("Chest(Clone)", "object:Chest")]
    [InlineData("Castle", "scenery:Castle")]
    [InlineData("Crate (2)", "scenery:Crate (2)")]
    [InlineData("Ruins (1)", "scenery:Ruins (1)")]
    public void Of_SplitsClonesFromUnclonedSceneryRoots(string rootName, string expected)
    {
        Assert.Equal(expected, SceneRootCategory.Of(rootName));
    }

    [Fact]
    public void Of_LeavesTheFogOfWarSphereOutOfTheIndex()
    {
        Assert.Null(SceneRootCategory.Of("FogOfWarSphere"));
    }
}
