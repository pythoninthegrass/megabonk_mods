namespace MegabonkLevels.Tests;

public class GenIdAssignerTests
{
    [Fact]
    public void Assign_NumbersItemsInSourceOrderWithFourDigitPadding()
    {
        var result = GenIdAssigner.Assign("tile", new[] { "a", "b", "c" });

        Assert.Equal(new[] { "tile:0000", "tile:0001", "tile:0002" }, result.Select(r => r.GenId));
        Assert.Equal(new[] { "a", "b", "c" }, result.Select(r => r.Item));
    }

    [Fact]
    public void Assign_KeepsSubcategoryInId()
    {
        var result = GenIdAssigner.Assign("randomObject:Tree", new[] { 1, 2 });

        Assert.Equal("randomObject:Tree:0001", result[1].GenId);
    }

    [Fact]
    public void Assign_EmptySource_ReturnsEmpty()
    {
        Assert.Empty(GenIdAssigner.Assign("chest", Array.Empty<int>()));
    }

    [Fact]
    public void Assign_BlankCategory_Throws()
    {
        Assert.Throws<ArgumentException>(() => GenIdAssigner.Assign(" ", new[] { 1 }));
    }

    [Fact]
    public void Index_MapsGenIdToItem()
    {
        var index = GenIdAssigner.Index(new Dictionary<string, IReadOnlyList<string>>
        {
            ["tile"] = new[] { "t0", "t1" },
            ["chest"] = new[] { "c0" },
        });

        Assert.Equal(3, index.Count);
        Assert.Equal("t1", index["tile:0001"]);
        Assert.Equal("c0", index["chest:0000"]);
    }
}
