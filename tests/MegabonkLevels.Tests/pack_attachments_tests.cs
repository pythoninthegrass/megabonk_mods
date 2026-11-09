namespace MegabonkLevels.Tests;

public class PackAttachmentsTests
{
    [Fact]
    public void Parse_ValidatesSchemaAndRetainsExplicitLocalMetadata()
    {
        var data = PackAttachments.Parse("""
            {"schema":"pack-attachments/1","assets":{"piece":[{
              "name":"path", "catalogId":"interactable/rail/0", "hidden":true,
              "localTransform":{"position":{"x":1,"y":2,"z":3},"rotation":{"x":0,"y":90,"z":0},"scale":{"x":1,"y":1,"z":1}}
            }]}}
            """);
        var child = Assert.Single(data["piece"]);
        Assert.True(child.Hidden);
        Assert.Equal(new Vector3Data(1, 2, 3), child.LocalTransform.Position);
    }

    [Theory]
    [InlineData("{}")]
    [InlineData("{\"schema\":\"pack-attachments/2\",\"assets\":{}}")]
    [InlineData("{\"schema\":\"pack-attachments/1\",\"assets\":null}")]
    [InlineData("{\"schema\":1,\"assets\":{}}")]
    [InlineData("{\"schema\":\"pack-attachments/1\",\"assets\":{\"piece\":null}}")]
    [InlineData("{\"schema\":\"pack-attachments/1\",\"assets\":{\"piece\":{}}}")]
    public void Parse_RejectsUnknownOrMissingSchemaAndAssets(string json)
    {
        Assert.Throws<ArgumentException>(() => PackAttachments.Parse(json));
    }

    [Fact]
    public void CommittedWarehouseMetadata_ParsesWithoutInventingLegacyAttachments()
    {
        var root = FindRoot();
        var data = PackAttachments.Parse(File.ReadAllText(Path.Combine(root, "unity/pack-authoring/packs/thps/attachments.json")));
        Assert.False(data.ContainsKey("Warehouse"));
        Assert.Equal(6, data["piece-rail-big-straight"].Count);
        Assert.Equal(58, data.Values.Sum(children => children.Count));
    }

    private static string FindRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory != null && !Directory.Exists(Path.Combine(directory.FullName, "src")))
        {
            directory = directory.Parent;
        }
        return directory!.FullName;
    }
}
