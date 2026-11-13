namespace MegabonkLevels;

// Decides whether the active run must stay off Steam: a custom level or a mod-added character is not something stock clients can decode.
public static class RunExclusion
{
    public const string CustomLevelReason = "custom-level run active";
    public const string ModCharacterReason = "mod character run active";

    // The character of the run in progress; kept past the player's destruction so an end-of-run upload is still excluded.
    public static int? CharacterId { get; private set; }

    public static void OnPlayerStarting(int characterId) => CharacterId = characterId;

    public static void Reset() => CharacterId = null;

    public static string Reason() => Reason(CustomLevelState.IsActive, CharacterId);

    // Null when the run may write to Steam, otherwise the reason it may not.
    public static string Reason(bool customLevelActive, int? characterId)
    {
        if (customLevelActive)
        {
            return CustomLevelReason;
        }

        return characterId is { } id && ModCharacterRegistration.IsModCharacter(id) ? ModCharacterReason : null;
    }
}
