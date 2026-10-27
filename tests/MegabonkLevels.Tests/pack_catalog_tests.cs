namespace MegabonkLevels.Tests;

public class PackCatalogTests
{
    private static readonly object Prop = new();

    private static PackCatalog<object> CatalogWith(Dictionary<string, Dictionary<string, object>> packs, List<string>? loads = null) =>
        new(pack =>
        {
            loads?.Add(pack);
            return packs.TryGetValue(pack, out var assets) ? assets : null;
        });

    [Fact]
    public void Resolve_InstalledPackAndAsset_ReturnsPrefab()
    {
        var catalog = CatalogWith(new() { ["testpack"] = new() { ["TestProp"] = Prop } });

        var lookup = catalog.Resolve(CatalogId.Parse("bundle:testpack/TestProp"));

        Assert.Equal(PackResolution.Found, lookup.Result);
        Assert.Same(Prop, lookup.Prefab);
    }

    [Fact]
    public void Resolve_UninstalledPack_ReportsPackMissing()
    {
        var catalog = CatalogWith(new());

        var lookup = catalog.Resolve(CatalogId.Parse("bundle:nopack/Thing"));

        Assert.Equal(PackResolution.PackMissing, lookup.Result);
        Assert.Null(lookup.Prefab);
    }

    [Fact]
    public void Resolve_AssetNotInPack_ReportsAssetMissing()
    {
        var catalog = CatalogWith(new() { ["testpack"] = new() { ["TestProp"] = Prop } });

        var lookup = catalog.Resolve(CatalogId.Parse("bundle:testpack/Other"));

        Assert.Equal(PackResolution.AssetMissing, lookup.Result);
        Assert.Null(lookup.Prefab);
    }

    [Fact]
    public void Resolve_AssetNameWithExtraSegments_ReportsAssetMissing()
    {
        var catalog = CatalogWith(new() { ["testpack"] = new() { ["TestProp"] = Prop } });

        var lookup = catalog.Resolve(CatalogId.Parse("bundle:testpack/TestProp/Extra"));

        Assert.Equal(PackResolution.AssetMissing, lookup.Result);
    }

    [Fact]
    public void Resolve_SamePackTwice_LoadsPackOnce()
    {
        var loads = new List<string>();
        var catalog = CatalogWith(new() { ["testpack"] = new() { ["A"] = Prop, ["B"] = Prop } }, loads);

        catalog.Resolve(CatalogId.Parse("bundle:testpack/A"));
        catalog.Resolve(CatalogId.Parse("bundle:testpack/B"));

        Assert.Equal(new[] { "testpack" }, loads);
    }

    [Fact]
    public void Resolve_UninstalledPackTwice_LoadsPackOnce()
    {
        var loads = new List<string>();
        var catalog = CatalogWith(new(), loads);

        catalog.Resolve(CatalogId.Parse("bundle:nopack/A"));
        catalog.Resolve(CatalogId.Parse("bundle:nopack/B"));

        Assert.Equal(new[] { "nopack" }, loads);
    }

    [Fact]
    public void Resolve_GameAssetId_Throws()
    {
        var catalog = CatalogWith(new());

        Assert.Throws<ArgumentException>(() => catalog.Resolve(CatalogId.Parse("interactable/chest")));
    }
}

public class PackFilesTests
{
    [Theory]
    [InlineData("testprop", true)]
    [InlineData("testprop.bundle", true)]
    [InlineData("TESTPROP.BUNDLE", true)]
    [InlineData("manifest.json", false)]
    [InlineData("readme.txt", false)]
    [InlineData("testprop.manifest", false)]
    [InlineData("", false)]
    public void IsBundleFile_MatchesExtensionlessAndBundleFiles(string fileName, bool expected)
    {
        Assert.Equal(expected, PackFiles.IsBundleFile(fileName));
    }
}
