using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

// Reads named public fields and properties off live objects by reflection, for the query-objects harness command.
public static class ObjectQuery
{
    private const BindingFlags Members = BindingFlags.Public | BindingFlags.Instance;

    public static Type ResolveType(IEnumerable<Type> candidates, string name)
    {
        var matches = candidates.Where(type => type.Name == name || type.FullName == name).ToList();
        return matches.Count switch
        {
            0 => throw new InvalidOperationException($"unknown type '{name}'"),
            1 => matches[0],
            _ => throw new InvalidOperationException($"type name '{name}' is ambiguous; use one of: {string.Join(", ", matches.Select(type => type.FullName))}"),
        };
    }

    // Checks the field names against the type first so an unknown one fails even when no instance is loaded.
    public static JsonObject Read(Type type, IEnumerable<object> items, IReadOnlyList<string> fields, int depth = 0)
    {
        var names = fields.Prepend("name").Distinct().ToList();
        var readers = names.Select(name => (name, reader: FindReader(type, name))).ToList();

        var rows = new JsonArray();
        foreach (var item in items)
        {
            var row = new JsonObject();
            foreach (var (name, reader) in readers)
            {
                row[name] = AssetDump.Describe(reader(item), depth);
            }

            rows.Add(row);
        }

        return new JsonObject { ["type"] = type.Name, ["count"] = rows.Count, ["objects"] = rows };
    }

    public static JsonObject ReadStatics(Type type, IReadOnlyList<string> fields, int depth = 0)
    {
        var row = new JsonObject { ["name"] = type.Name };
        foreach (var name in fields.Distinct().Where(name => name != "name"))
        {
            row[name] = AssetDump.Describe(FindReader(type, name, BindingFlags.Public | BindingFlags.Static)(null), depth);
        }

        return new JsonObject { ["type"] = type.Name, ["count"] = 1, ["objects"] = new JsonArray(row) };
    }

    private static Func<object, object> FindReader(Type type, string name, BindingFlags members = Members)
    {
        if (type.GetProperty(name, members) is { } property && property.GetIndexParameters().Length == 0)
        {
            return property.GetValue;
        }

        if (type.GetField(name, members) is { } field)
        {
            return field.GetValue;
        }

        throw new InvalidOperationException($"type '{type.Name}' has no public field '{name}'");
    }
}
