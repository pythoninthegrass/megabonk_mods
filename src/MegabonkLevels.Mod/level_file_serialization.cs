using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

public static class LevelFileSerializer
{
    // No real migration steps exist yet — schemaVersion 1 is the only version shipped so far.
    // Register a 1 -> 2 entry here when a future version 2 is introduced.
    private static readonly IReadOnlyDictionary<int, MigrationStep> ProductionSteps =
        new Dictionary<int, MigrationStep>();

    private static readonly JsonSerializerOptions Options = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };

    public static string Serialize(LevelFile level) => JsonSerializer.Serialize(level, Options);

    public static LevelFile Deserialize(string json) => JsonSerializer.Deserialize<LevelFile>(json, Options)!;

    public static LevelFile DeserializeWithMigration(string json)
    {
        var document = JsonNode.Parse(json)!.AsObject();
        var current = SchemaMigrator.Migrate(document, LevelFile.CurrentSchemaVersion, ProductionSteps);
        return current.Deserialize<LevelFile>(Options)!;
    }
}
