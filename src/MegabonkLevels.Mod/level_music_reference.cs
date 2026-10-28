namespace MegabonkLevels;

// A level's "music" value: a bundle:<pack>/<asset> catalogId naming an AudioClip inside an installed pack.
public readonly record struct LevelMusicReference(string Pack, string Asset)
{
    public static bool TryParse(string value, out LevelMusicReference reference)
    {
        reference = default;
        if (!CatalogId.TryParse(value, out var id, out _) || id.Namespace != CatalogNamespace.Bundle || id.Segments.Count != 2)
        {
            return false;
        }

        reference = new LevelMusicReference(id.Segments[0], id.Segments[1]);
        return true;
    }
}
