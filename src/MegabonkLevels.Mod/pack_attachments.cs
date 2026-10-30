using System;
using System.Collections.Generic;
using System.Text.Json;

namespace MegabonkLevels;

public static class PackAttachments
{
    public const string FileName = "attachments.json";

    public static IReadOnlyDictionary<string, IReadOnlyList<ObjectAttachmentSpec>> Parse(string json)
    {
        try
        {
            using var doc = JsonDocument.Parse(json);
            var root = doc.RootElement;
            if (root.ValueKind != JsonValueKind.Object
                || !root.TryGetProperty("schema", out var schema) || schema.ValueKind != JsonValueKind.String || schema.GetString() != "pack-attachments/1"
                || !root.TryGetProperty("assets", out var assets) || assets.ValueKind != JsonValueKind.Object)
            {
                throw new ArgumentException("Expected pack-attachments/1 with an assets object.");
            }
            var result = new Dictionary<string, IReadOnlyList<ObjectAttachmentSpec>>(StringComparer.Ordinal);
            foreach (var asset in assets.EnumerateObject())
            {
                if (asset.Value.ValueKind != JsonValueKind.Array)
                {
                    throw new ArgumentException($"Attachments for '{asset.Name}' must be an array.");
                }
                var children = JsonSerializer.Deserialize<ObjectAttachmentSpec[]>(asset.Value.GetRawText(), EditOpJson.Options);
                var validated = new PlaceObject("bundle:pack/" + asset.Name, default, default, new(1, 1, 1), Attachments: children);
                if (!result.TryAdd(asset.Name, validated.Attachments))
                {
                    throw new ArgumentException($"Duplicate attachment asset '{asset.Name}'.");
                }
            }
            return result;
        }
        catch (JsonException e)
        {
            throw new ArgumentException("Invalid pack attachment metadata.", nameof(json), e);
        }
    }
}
