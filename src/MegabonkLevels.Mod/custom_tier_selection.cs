namespace MegabonkLevels;

public interface ICustomTierMenu
{
    int TierCount { get; }
    void SetAvailable(int index, bool available);
    void RebuildNavigation();
    void SelectFirst();
}

public static class CustomTierSelection
{
    public static void Repair(ICustomTierMenu menu, bool select)
    {
        for (var i = 0; i < menu.TierCount; i++)
        {
            menu.SetAvailable(i, i == 0);
        }

        if (menu.TierCount > 0)
        {
            menu.RebuildNavigation();
            if (select)
            {
                menu.SelectFirst();
            }
        }
    }
}
