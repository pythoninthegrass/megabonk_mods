namespace MegabonkLevels;

// Compares a level file's recorded pack version against the version in the installed manifest so a
// pack that changed since the level was saved surfaces a warning instead of silently loading.
// Mirrors GameBuildIdCheck: a mismatch logs a warning and the run still starts, never blocking.
public static class GamePackVersionCheck
{
    public static string MismatchWarning(string packId, string recordedVersion, string installedVersion)
    {
        if (recordedVersion is null || installedVersion is null || recordedVersion == installedVersion)
        {
            return null;
        }

        return $"Pack '{packId}' was saved at version '{recordedVersion}' but the installed manifest is '{installedVersion}'; the level may not reproduce as expected.";
    }
}
