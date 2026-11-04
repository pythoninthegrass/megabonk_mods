using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace MegabonkLevels;

public readonly record struct ThumbnailSidecar(string Path, string Warning);

// Finds the jpg/png cover image named after a level file; see docs/level-format.md.
public static class LevelThumbnailSidecar
{
    public const long MaxBytes = 8 * 1024 * 1024;
    public const int MaxDimension = 4096;

    private const string LevelSuffix = ".mblevel.json";
    private static readonly string[] Extensions = { ".png", ".jpg", ".jpeg" };

    public static ThumbnailSidecar Find(string levelPath)
    {
        var fileName = Path.GetFileName(levelPath);
        var baseName = fileName.EndsWith(LevelSuffix, StringComparison.OrdinalIgnoreCase) ? fileName[..^LevelSuffix.Length] : Path.GetFileNameWithoutExtension(fileName);
        var folder = Path.GetDirectoryName(Path.GetFullPath(levelPath));

        string[] files;
        try
        {
            files = Directory.GetFiles(folder);
        }
        catch (Exception ex) when (ex is DirectoryNotFoundException)
        {
            return default;
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or ArgumentException or NotSupportedException)
        {
            return new ThumbnailSidecar(null, $"could not scan '{folder}' for a thumbnail: {ex.Message}.");
        }

        var candidates = files
            .Where(f => Extensions.Contains(Path.GetExtension(f), StringComparer.OrdinalIgnoreCase)
                && string.Equals(Path.GetFileNameWithoutExtension(f), baseName, StringComparison.OrdinalIgnoreCase))
            .OrderBy(f => f, StringComparer.Ordinal)
            .ToList();
        if (candidates.Count == 0)
        {
            return default;
        }

        if (string.IsNullOrWhiteSpace(baseName) || baseName.IndexOfAny(new[] { '/', '\\', ':' }) >= 0 || baseName.Any(char.IsControl))
        {
            return new ThumbnailSidecar(null, $"skipping thumbnail for invalid level name '{baseName}'.");
        }

        if (candidates.Count != 1)
        {
            return new ThumbnailSidecar(null, $"ambiguous thumbnail for '{baseName}': {string.Join(", ", candidates.Select(Path.GetFileName))}; keep one image.");
        }

        return Validate(candidates[0]);
    }

    public static bool TryReadDimensions(byte[] data, out int width, out int height)
    {
        width = height = 0;
        return TryReadPng(data, out width, out height) || TryReadJpeg(data, out width, out height);
    }

    public static bool DimensionsWithinLimit(int width, int height) =>
        width is > 0 and <= MaxDimension && height is > 0 and <= MaxDimension;

    private static ThumbnailSidecar Validate(string file)
    {
        var name = Path.GetFileName(file);
        try
        {
            if ((File.GetAttributes(file) & FileAttributes.ReparsePoint) != 0)
            {
                return new ThumbnailSidecar(null, $"skipping linked thumbnail '{name}'.");
            }

            var length = new FileInfo(file).Length;
            if (length == 0)
            {
                return new ThumbnailSidecar(null, $"thumbnail '{name}' is empty.");
            }

            if (length > MaxBytes)
            {
                return new ThumbnailSidecar(null, $"thumbnail '{name}' is {length} bytes, over the {MaxBytes} byte limit.");
            }
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        {
            return new ThumbnailSidecar(null, $"could not inspect thumbnail '{name}': {ex.Message}.");
        }

        return new ThumbnailSidecar(file, null);
    }

    private static bool TryReadPng(byte[] data, out int width, out int height)
    {
        width = height = 0;
        byte[] signature = { 0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A };
        byte[] ihdr = { 0x49, 0x48, 0x44, 0x52 };
        if (data.Length < 24 || !data.AsSpan(0, 8).SequenceEqual(signature) || !data.AsSpan(12, 4).SequenceEqual(ihdr))
        {
            return false;
        }

        width = System.Buffers.Binary.BinaryPrimitives.ReadInt32BigEndian(data.AsSpan(16));
        height = System.Buffers.Binary.BinaryPrimitives.ReadInt32BigEndian(data.AsSpan(20));
        return true;
    }

    private static bool TryReadJpeg(byte[] data, out int width, out int height)
    {
        width = height = 0;
        if (data.Length < 4 || data[0] != 0xFF || data[1] != 0xD8)
        {
            return false;
        }

        var i = 2;
        while (i + 4 <= data.Length)
        {
            if (data[i] != 0xFF)
            {
                return false;
            }

            var marker = data[i + 1];
            if (marker == 0xFF)
            {
                i++;
                continue;
            }

            if (marker is >= 0xC0 and <= 0xCF and not 0xC4 and not 0xC8 and not 0xCC)
            {
                if (i + 9 > data.Length)
                {
                    return false;
                }

                height = (data[i + 5] << 8) | data[i + 6];
                width = (data[i + 7] << 8) | data[i + 8];
                return true;
            }

            i += 2 + ((data[i + 2] << 8) | data[i + 3]);
        }

        return false;
    }
}
