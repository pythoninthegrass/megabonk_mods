using System;
using System.IO;

namespace MegabonkLevels;

// Where a screenshot lands: a relative path resolves under the evidence directory the launcher passes in, like the MCP tool.
public readonly record struct ScreenshotTarget(string Path, string Error);

public static class ScreenshotPath
{
    public const string EvidenceVariable = "MEGABONK_EVIDENCE_DIR";

    // An absolute path is used as given; a relative one under the evidence directory is refused when it already exists.
    public static ScreenshotTarget Resolve(string path, string evidenceDirectory, Func<string, bool> exists)
    {
        if (Path.IsPathRooted(path) || string.IsNullOrEmpty(evidenceDirectory))
        {
            return new ScreenshotTarget(path, null);
        }

        var full = Path.Combine(evidenceDirectory, path);
        return exists(full)
            ? new ScreenshotTarget(null, $"{full} already exists; choose another name")
            : new ScreenshotTarget(full, null);
    }
}
