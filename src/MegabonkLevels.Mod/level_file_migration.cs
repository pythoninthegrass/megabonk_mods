using System;
using System.Collections.Generic;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

public delegate JsonObject MigrationStep(JsonObject document);

// Applies registered schemaVersion -> schemaVersion+1 steps in sequence until targetVersion is reached.
// Adding a future schema version is one new entry in the steps dictionary, not a rewrite of this loop.
public static class SchemaMigrator
{
    public static JsonObject Migrate(JsonObject document, int targetVersion, IReadOnlyDictionary<int, MigrationStep> steps)
    {
        var current = document;
        var version = (int)current["schemaVersion"]!;

        while (version < targetVersion)
        {
            if (!steps.TryGetValue(version, out var step))
            {
                throw new InvalidOperationException($"No migration step registered for schemaVersion {version}");
            }

            current = step(current);
            version = (int)current["schemaVersion"]!;
        }

        return current;
    }
}
