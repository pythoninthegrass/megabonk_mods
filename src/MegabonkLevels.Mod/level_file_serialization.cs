using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

public static class LevelFileSerializer
{
    // Each entry migrates a document from the schemaVersion given by its key to the next one.
    private static readonly IReadOnlyDictionary<int, MigrationStep> ProductionSteps =
        new Dictionary<int, MigrationStep>
        {
            [1] = document =>
            {
                document["schemaVersion"] = 2;
                document["packs"] ??= new JsonObject();
                return document;
            },
            [2] = document =>
            {
                document["schemaVersion"] = 3;
                return document;
            },
            [3] = document =>
            {
                document["schemaVersion"] = 4;
                return document;
            },
        };

    private static readonly JsonSerializerOptions Options = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

    public static string Serialize(LevelFile level) => JsonSerializer.Serialize(level, Options);

    public static LevelFile Deserialize(string json) => Finish(JsonSerializer.Deserialize<LevelFile>(json, Options)!);

    public static LevelFile DeserializeWithMigration(string json)
    {
        var document = JsonNode.Parse(json)!.AsObject();
        var current = SchemaMigrator.Migrate(document, LevelFile.CurrentSchemaVersion, ProductionSteps);
        return Finish(current.Deserialize<LevelFile>(Options)!);
    }

    private static LevelFile Finish(LevelFile level)
    {
        var withPacks = WithPacks(level);
        LevelFileValidator.Validate(withPacks);
        return withPacks;
    }

    // A file without a packs key deserializes it as null; an empty map is the documented default.
    private static LevelFile WithPacks(LevelFile level) =>
        level.Packs is null ? level with { Packs = new Dictionary<string, string>() } : level;
}
