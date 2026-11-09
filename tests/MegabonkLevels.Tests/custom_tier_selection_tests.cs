namespace MegabonkLevels.Tests;

public class CustomTierSelectionTests
{
    private sealed class Menu : ICustomTierMenu
    {
        public int TierCount => 3;
        public bool[] Visible = { true, true, true };
        public bool[] Selectable = { false, true, true };
        public int Selected = 2;
        public List<string> Calls = new();

        public void SetAvailable(int index, bool available)
        {
            Visible[index] = Selectable[index] = available;
            Calls.Add($"available:{index}:{available}");
        }

        public void RebuildNavigation() => Calls.Add("navigation");
        public void SelectFirst()
        {
            Assert.True(Visible[0] && Selectable[0]);
            Assert.Equal("navigation", Calls[^1]);
            Selected = 0;
            Calls.Add("select");
        }
    }

    [Fact]
    public void Repair_ReplacesLockedFirstTierAndStaleHigherSelection()
    {
        var menu = new Menu();
        CustomTierSelection.Repair(menu, select: true);
        Assert.Equal(new[] { true, false, false }, menu.Visible);
        Assert.Equal(new[] { true, false, false }, menu.Selectable);
        Assert.Equal(0, menu.Selected);
        Assert.Equal(new[] { "available:0:True", "available:1:False", "available:2:False", "navigation", "select" }, menu.Calls);
    }

    [Fact]
    public void Refresh_RepairsLinksWithoutSelectingBeforeNativeMapSelectionFinishes()
    {
        var menu = new Menu();
        CustomTierSelection.Repair(menu, select: false);
        Assert.Equal(2, menu.Selected);
        Assert.Equal("navigation", menu.Calls[^1]);
        Assert.DoesNotContain("select", menu.Calls);
        Assert.True(menu.Selectable[0]);
    }

    [Fact]
    public void Repair_CanBeRepeatedAfterNativeRefreshRestoresAllTiers()
    {
        var menu = new Menu();
        CustomTierSelection.Repair(menu, select: true);
        Array.Fill(menu.Visible, true);
        menu.Selected = 2;
        CustomTierSelection.Repair(menu, select: true);
        Assert.Equal(new[] { true, false, false }, menu.Visible);
        Assert.Equal(0, menu.Selected);
    }
}
