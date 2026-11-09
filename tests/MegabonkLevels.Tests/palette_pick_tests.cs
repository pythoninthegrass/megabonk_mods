namespace MegabonkLevels.Tests;

public class PalettePickTests
{
    private static PaletteEntry Entry(string id, string name, PaletteCategory category, int stage) =>
        new(CatalogId.Parse(id), name, category, stage);

    private static readonly PaletteEntry Stage0Tree = Entry("forest/stage0/randomMapObjects/0/0", "Tree0", PaletteCategory.RandomObject, 0);
    private static readonly PaletteEntry Stage1Tree = Entry("forest/stage1/randomMapObjects/0/0", "Tree0", PaletteCategory.RandomObject, 1);
    private static readonly PaletteEntry Chest = Entry("interactable/chest", "Chest", PaletteCategory.Interactable, 0);
    private static readonly PaletteEntry[] Entries = { Stage0Tree, Stage1Tree, Chest };

    [Fact]
    public void FindByPrefabName_PrefersTheCurrentStage()
    {
        Assert.Equal(Stage1Tree, PalettePick.FindByPrefabName(Entries, "Tree0", 1));
    }

    [Fact]
    public void FindByPrefabName_FallsBackToStageIndependentEntries()
    {
        Assert.Equal(Chest, PalettePick.FindByPrefabName(Entries, "Chest", 1));
    }

    [Fact]
    public void FindByPrefabName_OtherStageOnly_ReturnsNull()
    {
        Assert.Null(PalettePick.FindByPrefabName(new[] { Stage0Tree }, "Tree0", 2));
    }

    [Fact]
    public void FindByPrefabName_UnknownName_ReturnsNull()
    {
        Assert.Null(PalettePick.FindByPrefabName(Entries, "Rock", 0));
    }

    [Fact]
    public void FindByCatalogId_ReturnsTheEntry()
    {
        Assert.Equal(Stage1Tree, PalettePick.FindByCatalogId(Entries, Stage1Tree.Id));
    }

    [Fact]
    public void FindByCatalogId_Missing_ReturnsNull()
    {
        Assert.Null(PalettePick.FindByCatalogId(new[] { Chest }, Stage1Tree.Id));
    }

    [Fact]
    public void FindByPrefabName_PrefersTheLoadedMap()
    {
        var forestTree = Entry("forest/stage0/randomMapObjects/0/0", "Palm", PaletteCategory.RandomObject, 0) with { Map = EMap.Forest };
        var desertTree = Entry("desert/stage0/randomMapObjects/0/0", "Palm", PaletteCategory.RandomObject, 0) with { Map = EMap.Desert };
        var entries = new[] { forestTree, desertTree };

        Assert.Equal(desertTree, PalettePick.FindByPrefabName(entries, "Palm", 0, EMap.Desert));
        Assert.Equal(forestTree, PalettePick.FindByPrefabName(entries, "Palm", 0, EMap.Forest));
    }

    [Fact]
    public void FindByPrefabName_MaplessEntriesMatchAnyLoadedMap()
    {
        var pack = Entry("bundle:thps/rail", "Rail", PaletteCategory.Pack, 0);
        var shrine = Entry("forest/shrines/0", "Rail", PaletteCategory.Shrine, 0) with { Map = EMap.Forest };

        Assert.Equal(pack, PalettePick.FindByPrefabName(new[] { pack, shrine }, "Rail", 0, EMap.Graveyard));
    }

    [Fact]
    public void FindByPrefabName_OnlyOtherMap_StillFindsIt()
    {
        var desertTree = Entry("desert/stage0/randomMapObjects/0/0", "Palm", PaletteCategory.RandomObject, 0) with { Map = EMap.Desert };

        Assert.Equal(desertTree, PalettePick.FindByPrefabName(new[] { desertTree }, "Palm", 0, EMap.Forest));
    }

    [Theory]
    [InlineData("object:Tree0:0003", "Tree0")]
    [InlineData("tileObject:0001", null)]
    [InlineData("object:Chest:0000", "Chest")]
    public void PrefabNameOf_ReadsTheCategoryOfAnObjectGenId(string genId, string? expected)
    {
        Assert.Equal(expected, PalettePick.PrefabNameOf(genId));
    }
}
