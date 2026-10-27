namespace MegabonkLevels.Tests;

public class PackManifestParseTests
{
    private static string Manifest(
        string id = "testpack",
        string name = "Test Pack",
        string author = "tester",
        string version = "1.2.3",
        string assets = null)
    {
        var assetList = assets ?? "[\"Rock\", \"Chest\"]";
        return $"\"id\": \"{id}\", \"name\": \"{name}\", \"author\": \"{author}\", \"version\": \"{version}\", \"assets\": {assetList}";
    }

    [Fact]
    public void Parse_ValidManifest_ReturnsAllFields()
    {
        var manifest = PackManifest.Parse($"{{{Manifest()}}}", "testpack");

        Assert.Equal("testpack", manifest.Id);
        Assert.Equal("Test Pack", manifest.Name);
        Assert.Equal("tester", manifest.Author);
        Assert.Equal("1.2.3", manifest.Version);
        Assert.Equal(new[] { "Rock", "Chest" }, manifest.Assets);
    }

    [Fact]
    public void Parse_EmptyAssets_ReturnsNoAssets()
    {
        var manifest = PackManifest.Parse($"{{{Manifest(assets: "[]")}}}", "testpack");

        Assert.Empty(manifest.Assets);
    }

    [Fact]
    public void Parse_MalformedJson_Throws()
    {
        Assert.Throws<InvalidOperationException>(() => PackManifest.Parse("this is not json", "testpack"));
    }

    [Fact]
    public void Parse_NotAnObject_Throws()
    {
        Assert.Throws<InvalidOperationException>(() => PackManifest.Parse("[1, 2, 3]", "testpack"));
    }

    [Theory]
    [InlineData("id")]
    [InlineData("name")]
    [InlineData("author")]
    [InlineData("version")]
    [InlineData("assets")]
    public void Parse_MissingRequiredField_Throws(string missingField)
    {
        var json = Manifest();
        var without = json.Replace($"\"{missingField}\"", "\"__removed__\"");

        Assert.Throws<InvalidOperationException>(() => PackManifest.Parse($"{{{without}}}", "testpack"));
    }

    [Fact]
    public void Parse_AssetsNotAList_Throws()
    {
        Assert.Throws<InvalidOperationException>(() => PackManifest.Parse($"{{{Manifest(assets: "\"Rock\"")}}}", "testpack"));
    }

    [Fact]
    public void Parse_AssetsNonStringElements_Throws()
    {
        Assert.Throws<InvalidOperationException>(() => PackManifest.Parse($"{{{Manifest(assets: "[\"Rock\", 5]")}}}", "testpack"));
    }

    [Fact]
    public void Parse_AssetsAnObject_Throws()
    {
        var ex = Assert.Throws<InvalidOperationException>(() => PackManifest.Parse($"{{{Manifest(assets: "{}")}}}", "testpack"));

        Assert.Contains("assets", ex.Message);
    }

    [Fact]
    public void Parse_IdDiffersFromFolderName_Throws()
    {
        var ex = Assert.Throws<InvalidOperationException>(() => PackManifest.Parse($"{{{Manifest(id: "otherpack")}}}", "testpack"));

        Assert.Contains("otherpack", ex.Message);
        Assert.Contains("testpack", ex.Message);
    }
}
