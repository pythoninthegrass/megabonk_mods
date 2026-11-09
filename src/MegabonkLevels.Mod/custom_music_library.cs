using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace MegabonkLevels;

public sealed class CustomMusicLibrary
{
    private readonly Dictionary<string, string> _paths = new(StringComparer.OrdinalIgnoreCase);

    public IReadOnlyList<string> Names { get; private set; } = Array.Empty<string>();

    public string Resolve(string name) => name != null && _paths.TryGetValue(name, out var path) ? path : null;

    public static CustomMusicLibrary Discover(string folder, Action<string> warning = null)
    {
        var library = new CustomMusicLibrary();
        string[] files;
        try
        {
            files = Directory.GetFiles(Path.GetFullPath(folder));
        }
        catch (DirectoryNotFoundException)
        {
            if (File.Exists(folder))
            {
                warning?.Invoke("Music: custom music folder is a file, not a directory.");
            }

            return library;
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or ArgumentException or NotSupportedException)
        {
            warning?.Invoke($"Music: could not scan custom music folder: {ex.Message}.");
            return library;
        }

        var candidates = new List<string>();
        foreach (var file in files.Where(file => string.Equals(Path.GetExtension(file), ".mp3", StringComparison.OrdinalIgnoreCase)).OrderBy(file => file, StringComparer.Ordinal))
        {
            try
            {
                if ((File.GetAttributes(file) & FileAttributes.ReparsePoint) != 0)
                {
                    warning?.Invoke($"Music: skipping linked file '{Path.GetFileName(file)}'.");
                    continue;
                }

                candidates.Add(file);
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
            {
                warning?.Invoke($"Music: could not inspect '{Path.GetFileName(file)}': {ex.Message}.");
            }
        }

        return FromFiles(candidates, warning);
    }

    internal static CustomMusicLibrary FromFiles(IEnumerable<string> files, Action<string> warning = null)
    {
        var library = new CustomMusicLibrary();
        foreach (var group in files.OrderBy(file => file, StringComparer.Ordinal).GroupBy(file => Path.GetFileNameWithoutExtension(file), StringComparer.OrdinalIgnoreCase))
        {
            if (group.Count() != 1)
            {
                warning?.Invoke($"Music: ambiguous custom track '{group.Key}'; rename case-colliding files.");
                continue;
            }

            if (string.IsNullOrWhiteSpace(group.Key) || group.Key.IndexOfAny(new[] { '/', '\\', ':' }) >= 0 || group.Key.Any(char.IsControl))
            {
                warning?.Invoke($"Music: skipping invalid custom track name '{group.Key}'.");
                continue;
            }

            library._paths.Add(group.Key, group.Single());
        }

        library.Names = Array.AsReadOnly(library._paths.Keys.OrderBy(name => name, TrackFileName.Comparer).ToArray());
        return library;
    }
}
