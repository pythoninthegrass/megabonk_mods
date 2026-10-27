namespace MegabonkLevels.Tests;

public class UiWidgetsTests
{
    private static readonly UiWidget[] Widgets =
    {
        new("Save", 100f, 20f, 70f, 30f),
        new("Undo", 10f, 20f, 88f, 30f),
        new("Toolbar", 0f, 0f, 500f, 116f),
    };

    [Fact]
    public void Centre_IsTheMiddleOfTheRect()
    {
        Assert.Equal((135f, 35f), Widgets[0].Centre);
    }

    [Fact]
    public void At_ReturnsTheFirstWidgetUnderThePoint()
    {
        Assert.Equal("Save", UiWidgets.At(Widgets, 135f, 35f)?.Name);
        Assert.Equal("Toolbar", UiWidgets.At(Widgets, 300f, 100f)?.Name);
    }

    [Fact]
    public void At_ReturnsNullOutsideEveryWidget()
    {
        Assert.Null(UiWidgets.At(Widgets, 900f, 900f));
    }

    [Fact]
    public void At_IncludesTheTopLeftEdgeAndExcludesTheBottomRight()
    {
        Assert.Equal("Undo", UiWidgets.At(Widgets, 10f, 20f)?.Name);
        Assert.Equal("Toolbar", UiWidgets.At(Widgets, 170f, 50f)?.Name);
    }

    [Fact]
    public void TryFind_MatchesCaseInsensitively()
    {
        Assert.True(UiWidgets.TryFind(Widgets, "save", out var widget, out var error));
        Assert.Equal("Save", widget.Name);
        Assert.Null(error);
    }

    [Fact]
    public void TryFind_ListsTheKnownNamesOnAMiss()
    {
        Assert.False(UiWidgets.TryFind(Widgets, "Nope", out _, out var error));
        Assert.Contains("'Nope'", error);
        Assert.Contains("Save, Undo, Toolbar", error);
    }

    [Fact]
    public void FromScreenRect_FlipsUnityBottomLeftIntoTopLeftPixels()
    {
        var widget = UiWidgets.FromScreenRect("Save", xMin: 100f, yMin: 1000f, xMax: 170f, yMax: 1030f, screenHeight: 1080);

        Assert.Equal(new UiWidget("Save", 100f, 50f, 70f, 30f), widget);
    }

    [Fact]
    public void Widgets_AreEnabledUnlessMarkedOtherwise()
    {
        Assert.True(Widgets[0].Enabled);
        Assert.False(UiWidgets.FromScreenRect("Undo", 0f, 0f, 1f, 1f, 10, enabled: false).Enabled);
    }

    [Fact]
    public void At_ReportsADisabledWidget()
    {
        var disabled = new[] { new UiWidget("Undo", 0f, 0f, 10f, 10f, Enabled: false) };

        Assert.Equal("Undo", UiWidgets.At(disabled, 5f, 5f)?.Name);
    }
}
