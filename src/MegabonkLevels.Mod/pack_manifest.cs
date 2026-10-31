using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

// A pack's manifest.json at UserData/LevelPacks/<packId>/manifest.json. Parsing/validation is
// Unity-free and unit-tested; PackPrefabs reads the file and PackCatalog filters assets by it.
public readonly record struct PackManifest(
    string Id,
    string Name,
    string Author,
    string Version,
    IReadOnlyList<string> Assets,
    string KitVersion = null,
    IReadOnlyList<string> KitAssetPrefixes = null)
{
    public const string FileName = "manifest.json";

    public static PackManifest Parse(string json, string packFolder)
    {
        JsonObject root;
        try
        {
            root = JsonNode.Parse(json)?.AsObject()
                ?? throw new InvalidOperationException("manifest is empty or not a JSON object.");
        }
        catch (JsonException ex)
        {
            throw new InvalidOperationException($"manifest is not valid JSON: {ex.Message}", ex);
        }

        var id = RequireString(root, "id");
        var name = RequireString(root, "name");
        var author = RequireString(root, "author");
        var version = RequireString(root, "version");
        var assets = RequireAssets(root, "assets");

        if (id != packFolder)
        {
            throw new InvalidOperationException($"manifest id '{id}' does not match its pack folder '{packFolder}'.");
        }

        var kitVersion = root.ContainsKey("kitVersion") ? RequireString(root, "kitVersion") : null;
        var prefixes = root.ContainsKey("kitAssetPrefixes") ? RequireAssets(root, "kitAssetPrefixes") : Array.Empty<string>();
        if (kitVersion != null && (string.IsNullOrWhiteSpace(kitVersion) || prefixes.Count == 0 || prefixes.Any(string.IsNullOrWhiteSpace)))
        {
            throw new InvalidOperationException("kitVersion requires nonempty kitAssetPrefixes.");
        }
        return new PackManifest(id, name, author, version, assets, kitVersion, prefixes);
    }

    public bool IsKitAsset(string asset) => Assets.Contains(asset) && KitAssetPrefixes != null && KitAssetPrefixes.Any(prefix => asset.StartsWith(prefix, StringComparison.Ordinal));

    private static string RequireString(JsonObject root, string field)
    {
        var node = root[field];
        if (node is not JsonValue)
        {
            throw new InvalidOperationException($"manifest is missing required string field '{field}'.");
        }

        try
        {
            return JsonSerializer.Deserialize<string>(node) ?? string.Empty;
        }
        catch (JsonException ex)
        {
            throw new InvalidOperationException($"manifest field '{field}' must be a string.", ex);
        }
    }

    private static IReadOnlyList<string> RequireAssets(JsonObject root, string field)
    {
        var node = root[field];
        if (node is not JsonArray array)
        {
            throw new InvalidOperationException($"manifest is missing required array field '{field}'.");
        }

        var assets = new List<string>();
        foreach (var item in array)
        {
            string text;
            try
            {
                text = JsonSerializer.Deserialize<string>(item) ?? string.Empty;
            }
            catch (JsonException ex)
            {
                throw new InvalidOperationException($"manifest field '{field}' must be a list of strings.", ex);
            }

            if (item is not JsonValue)
            {
                throw new InvalidOperationException($"manifest field '{field}' must be a list of strings.");
            }

            assets.Add(text);
        }

        return assets;
    }
}
