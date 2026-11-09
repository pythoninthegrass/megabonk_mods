namespace MegabonkLevels.Tests;

public class PackPaletteEntriesTests
{
    private static PackManifest ManifestListing(string pack, params string[] assets) =>
        new(pack, "Name", "tester", "1.0.0", assets);

    private static PackPaletteListing Build(
        string[] packs,
        Dictionary<string, string[]> bundles,
        Dictionary<string, PackManifest>? manifests = null) =>
        PackPaletteEntries.Build(
            packs,
            pack => bundles.TryGetValue(pack, out var names) ? names : null,
            pack => manifests is not null && manifests.TryGetValue(pack, out var manifest) ? manifest : null);

    [Fact]
    public void Build_NoPacks_ReturnsNoEntries()
    {
        var listing = Build([], []);

        Assert.Empty(listing.Entries);
        Assert.Empty(listing.MissingFromBundle);
    }

    [Fact]
    public void Build_PackNotLoadable_IsSkipped()
    {
        var listing = Build(["ghost"], []);

        Assert.Empty(listing.Entries);
    }

    [Fact]
    public void Build_ManifestListedAssetInBundle_IsListedWithPackShape()
    {
        var listing = Build(
            ["testpack"],
            new() { ["testpack"] = ["TestProp"] },
            new() { ["testpack"] = ManifestListing("testpack", "TestProp") });

        var entry = Assert.Single(listing.Entries);
        Assert.Equal("bundle:testpack/TestProp", entry.Id.Serialize());
        Assert.Equal("TestProp", entry.DisplayName);
        Assert.Equal(PaletteCategory.Pack, entry.Category);
        Assert.Equal(0, entry.Stage);
    }

    [Fact]
    public void Build_ManifestListsAssetBundleLacks_ReportsItAndDoesNotList()
    {
        var listing = Build(
            ["testpack"],
            new() { ["testpack"] = ["TestProp"] },
            new() { ["testpack"] = ManifestListing("testpack", "TestProp", "Gone") });

        Assert.Equal(["bundle:testpack/TestProp"], listing.Entries.Select(e => e.Id.Serialize()));
        Assert.Equal([("testpack", "Gone")], listing.MissingFromBundle);
    }

    [Fact]
    public void Build_BundleHoldsAssetManifestOmits_DoesNotList()
    {
        var listing = Build(
            ["testpack"],
            new() { ["testpack"] = ["TestProp", "Extra"] },
            new() { ["testpack"] = ManifestListing("testpack", "TestProp") });

        Assert.Equal(["TestProp"], listing.Entries.Select(e => e.DisplayName));
        Assert.Empty(listing.MissingFromBundle);
    }

    [Fact]
    public void Build_NoManifest_ListsEveryBundleAsset()
    {
        var listing = Build(["testpack"], new() { ["testpack"] = ["B", "A"] });

        Assert.Equal(["A", "B"], listing.Entries.Select(e => e.DisplayName));
        Assert.Empty(listing.MissingFromBundle);
    }

    [Fact]
    public void Build_MultiplePacks_OrdersByPackThenAsset()
    {
        var listing = Build(
            ["zeta", "alpha"],
            new() { ["zeta"] = ["A"], ["alpha"] = ["Z", "B"] });

        Assert.Equal(
            ["bundle:alpha/B", "bundle:alpha/Z", "bundle:zeta/A"],
            listing.Entries.Select(e => e.Id.Serialize()));
    }

    [Fact]
    public void Filter_SearchByPackIdAndAssetName_MatchesBoth()
    {
        var entries = Build(
            ["alpha", "beta"],
            new() { ["alpha"] = ["Crate"], ["beta"] = ["Barrel"] }).Entries;

        Assert.Equal(["Crate"], PaletteFilter.Apply(entries, "alpha", null).Select(e => e.DisplayName));
        Assert.Equal(["Barrel"], PaletteFilter.Apply(entries, "barr", null).Select(e => e.DisplayName));
    }

    [Fact]
    public void Categories_PackAppearsOnlyWithEntries()
    {
        var withPack = Build(["alpha"], new() { ["alpha"] = ["Crate"] }).Entries;
        var without = Build([], []).Entries;

        Assert.Equal([PaletteCategory.Pack], PaletteFilter.Categories(withPack));
        Assert.Empty(PaletteFilter.Categories(without));
    }

    [Fact]
    public void PickByPrefabName_PackEntryIsFoundOnAnyStage()
    {
        var entries = Build(["alpha"], new() { ["alpha"] = ["Crate"] }).Entries;

        var found = PalettePick.FindByPrefabName(entries, "Crate", currentStage: 2);

        Assert.Equal("bundle:alpha/Crate", found?.Id.Serialize());
    }
}
