namespace MegabonkLevels.Tests;

public class EditorMapSupportTests
{
    [Fact]
    public void Check_TilesMap_IsSupportedWithTileTools()
    {
        var support = EditorMapSupport.Check("Forest", EditorMapSupport.TilesMapType);

        Assert.True(support.Supported);
        Assert.True(support.TileTools);
        Assert.Equal("", support.Reason);
    }

    [Fact]
    public void Check_ProceduralMeshMap_IsSupportedWithoutTileToolsAndNamesTheMap()
    {
        var support = EditorMapSupport.Check("Desert", EditorMapSupport.ProceduralMeshMapType);

        Assert.True(support.Supported);
        Assert.False(support.TileTools);
        Assert.Contains("Desert", support.Reason);
        Assert.Contains("tile", support.Reason, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Check_UnknownMapType_IsUnsupported()
    {
        var support = EditorMapSupport.Check("Mystery", -1);

        Assert.False(support.Supported);
        Assert.False(support.TileTools);
        Assert.Contains("Mystery", support.Reason);
    }
}
