using System;
using System.Collections;
using System.Collections.Generic;
using System.Reflection;
using System.Text.Json.Nodes;

namespace MegabonkLevels;

// Reflection walker behind query-objects: describes a live asset as JSON, expanding nested objects and arrays up to a caller-chosen depth.
// Depth bounds how many object levels open; the node budget and level cap keep a pathological asset graph from wedging the game thread.
public static class AssetDump
{
    public const int MaxDepth = 6;

    public const int DefaultMaxItems = 64;

    public const int DefaultMaxNodes = 20000;

    private const int MaxLevel = 24;

    private const BindingFlags Members = BindingFlags.Public | BindingFlags.Instance;

    public static JsonNode Describe(object value, int depth, int maxItems = DefaultMaxItems, int maxNodes = DefaultMaxNodes) =>
        Describe(value, Math.Min(depth, MaxDepth), new Walk(Math.Max(1, maxItems), Math.Max(1, maxNodes)));

    private static JsonNode Describe(object value, int depth, Walk walk)
    {
        if (value == null)
        {
            return null;
        }

        if (IsPrimitive(value, out var primitive))
        {
            return primitive;
        }

        if (walk.Nodes >= walk.MaxNodes || walk.Level >= MaxLevel)
        {
            return new JsonObject { ["$truncated"] = true };
        }

        walk.Nodes++;
        if (walk.Path.Contains(value))
        {
            return new JsonObject { ["$type"] = value.GetType().Name, ["name"] = ReadName(value), ["$cycle"] = true };
        }

        if (value is IEnumerable sequence)
        {
            return DescribeSequence(sequence, depth, walk);
        }

        if (depth <= 0)
        {
            return JsonValue.Create(SafeText(value));
        }

        var type = value.GetType();
        var fieldsOnly = Inherits(type, "UnityEngine.Object") && !Inherits(type, "UnityEngine.ScriptableObject");
        walk.Path.Add(value);
        walk.Level++;
        var node = new JsonObject { ["$type"] = type.Name };
        if (fieldsOnly)
        {
            node["name"] = JsonValue.Create(ReadName(value));
        }

        foreach (var member in MembersOf(type, fieldsOnly))
        {
            node[member.Key] = DescribeMember(member, value, depth - 1, walk);
        }

        walk.Level--;
        walk.Path.Remove(value);
        if (fieldsOnly)
        {
            node["$fieldsOnly"] = true;
        }

        return node;
    }

    // Engine objects expose properties that run game code (component lookups, texture uploads), so only their fields are read.
    private static bool Inherits(Type type, string fullName)
    {
        for (var current = type.BaseType; current != null; current = current.BaseType)
        {
            if (current.FullName == fullName)
            {
                return true;
            }
        }

        return false;
    }

    // A container is transparent: its items are described at the same depth as the container itself.
    private static JsonNode DescribeSequence(IEnumerable sequence, int depth, Walk walk)
    {
        walk.Path.Add(sequence);
        walk.Level++;
        var items = new JsonArray();
        var count = 0;
        foreach (var item in sequence)
        {
            count++;
            if (items.Count < walk.MaxItems)
            {
                items.Add(Describe(item, depth, walk));
            }
        }

        walk.Level--;
        walk.Path.Remove(sequence);
        if (count <= walk.MaxItems)
        {
            return items;
        }

        return new JsonObject { ["count"] = JsonValue.Create((long)count), ["truncated"] = true, ["items"] = items };
    }

    private static JsonNode DescribeMember(KeyValuePair<string, Func<object, object>> member, object owner, int depth, Walk walk)
    {
        object value;
        try
        {
            value = member.Value(owner);
        }
        catch (Exception ex)
        {
            var failure = ex is TargetInvocationException wrapped && wrapped.InnerException != null ? wrapped.InnerException : ex;
            return JsonValue.Create($"$error: {failure.GetType().Name}: {failure.Message}");
        }

        return Describe(value, depth, walk);
    }

    private static IEnumerable<KeyValuePair<string, Func<object, object>>> MembersOf(Type type, bool fieldsOnly)
    {
        foreach (var field in type.GetFields(Members))
        {
            yield return new KeyValuePair<string, Func<object, object>>(field.Name, instance => field.GetValue(instance));
        }

        if (fieldsOnly)
        {
            yield break;
        }

        foreach (var property in type.GetProperties(Members))
        {
            if (property.GetIndexParameters().Length != 0 || property.GetMethod == null)
            {
                continue;
            }

            yield return new KeyValuePair<string, Func<object, object>>(property.Name, instance => property.GetValue(instance));
        }
    }

    private static bool IsPrimitive(object value, out JsonNode primitive)
    {
        primitive = value switch
        {
            string text => JsonValue.Create(text),
            bool flag => JsonValue.Create(flag),
            Enum enumerated => JsonValue.Create(Convert.ToInt64(enumerated)),
            sbyte or byte or short or ushort or int or uint or long => JsonValue.Create(Convert.ToInt64(value)),
            ulong number => JsonValue.Create(number),
            float single => JsonValue.Create(single),
            double or decimal => JsonValue.Create(Convert.ToDouble(value)),
            char letter => JsonValue.Create(letter.ToString()),
            _ => null,
        };

        return primitive != null || value is string or bool;
    }

    private static string ReadName(object value)
    {
        try
        {
            return value.GetType().GetProperty("name", Members)?.GetValue(value) as string
                ?? value.GetType().GetField("name", Members)?.GetValue(value) as string;
        }
        catch (Exception ex)
        {
            return $"$error: {ex.GetType().Name}: {ex.Message}";
        }
    }

    private static string SafeText(object value)
    {
        try
        {
            return value.ToString() ?? value.GetType().Name;
        }
        catch (Exception ex)
        {
            return $"$error: {ex.GetType().Name}: {ex.Message}";
        }
    }

    // Per-walk state: the chain being expanded, and how much of the budget is left.
    private sealed class Walk
    {
        public Walk(int maxItems, int maxNodes)
        {
            MaxItems = maxItems;
            MaxNodes = maxNodes;
        }

        public HashSet<object> Path { get; } = new();

        public int MaxItems { get; }

        public int MaxNodes { get; }

        public int Nodes { get; set; }

        public int Level { get; set; }
    }
}
