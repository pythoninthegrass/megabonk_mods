namespace MegabonkLevels;

public static class MenuBackout
{
    public static bool ShouldCancel(bool held, bool restricted, bool movingToMaps) =>
        (held || restricted) && !movingToMaps;
}
