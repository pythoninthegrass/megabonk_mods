namespace MegabonkLevels.Tests;

public class EditorMapSupportTests
{
    [Fact]
    public void Check_TilesMap_IsSupported()
    {
        var support = EditorMapSupport.Check("Forest", EditorMapSupport.TilesMapType);

        Assert.True(support.Supported);
        Assert.Equal("", support.Reason);
    }

    [Fact]
    public void Check_ProceduralMeshMap_IsUnsupportedAndNamesTheMap()
    {
        var support = EditorMapSupport.Check("Desert", EditorMapSupport.ProceduralMeshMapType);

        Assert.False(support.Supported);
        Assert.Contains("Desert", support.Reason);
        Assert.Contains("tile", support.Reason, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void Check_UnknownMapType_IsUnsupported()
    {
        Assert.False(EditorMapSupport.Check("Mystery", -1).Supported);
    }
}
