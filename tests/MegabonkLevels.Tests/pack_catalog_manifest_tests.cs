namespace MegabonkLevels.Tests;

public class PackCatalogManifestTests
{
    private static PackCatalog<object> CatalogWith(
        Dictionary<string, Dictionary<string, object>> packs,
        Dictionary<string, PackManifest> manifests,
        List<string>? manifestReads = null) =>
        new(
            pack => packs.TryGetValue(pack, out var assets) ? assets : null,
            pack =>
            {
                manifestReads?.Add(pack);
                return manifests.TryGetValue(pack, out var manifest) ? manifest : null;
            });

    private static PackManifest ManifestListing(params string[] assets) =>
        new("testpack", "Test Pack", "tester", "1.0.0", assets);

    [Fact]
    public void Resolve_AssetInManifest_ReturnsFound()
    {
        var catalog = CatalogWith(
            new() { ["testpack"] = new() { ["TestProp"] = new() } },
            new() { ["testpack"] = ManifestListing("TestProp") });

        var lookup = catalog.Resolve(CatalogId.Parse("bundle:testpack/TestProp"));

        Assert.Equal(PackResolution.Found, lookup.Result);
    }

    [Fact]
    public void Resolve_AssetInBundleButNotManifest_ReportsAssetMissing()
    {
        var catalog = CatalogWith(
            new() { ["testpack"] = new() { ["TestProp"] = new() } },
            new() { ["testpack"] = ManifestListing("Other") });

        var lookup = catalog.Resolve(CatalogId.Parse("bundle:testpack/TestProp"));

        Assert.Equal(PackResolution.AssetMissing, lookup.Result);
        Assert.Null(lookup.Prefab);
    }

    [Fact]
    public void Resolve_PackWithoutManifest_DoesNotFilterAssets()
    {
        var catalog = CatalogWith(
            new() { ["testpack"] = new() { ["TestProp"] = new() } },
            new());

        var lookup = catalog.Resolve(CatalogId.Parse("bundle:testpack/TestProp"));

        Assert.Equal(PackResolution.Found, lookup.Result);
    }

    [Fact]
    public void Resolve_PackMissing_ReportsPackMissing()
    {
        var catalog = CatalogWith(new(), new());

        var lookup = catalog.Resolve(CatalogId.Parse("bundle:nopack/Thing"));

        Assert.Equal(PackResolution.PackMissing, lookup.Result);
    }

    [Fact]
    public void Resolve_SamePackTwice_ReadsManifestOnce()
    {
        var reads = new List<string>();
        var catalog = CatalogWith(
            new() { ["testpack"] = new() { ["A"] = new(), ["B"] = new() } },
            new() { ["testpack"] = ManifestListing("A", "B") },
            reads);

        catalog.Resolve(CatalogId.Parse("bundle:testpack/A"));
        catalog.Resolve(CatalogId.Parse("bundle:testpack/B"));

        Assert.Single(reads);
    }
}
