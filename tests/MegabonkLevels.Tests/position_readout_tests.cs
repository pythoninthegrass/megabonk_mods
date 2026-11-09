namespace MegabonkLevels.Tests;

public class PositionReadoutTests
{
    private const int Width = 15;
    private const int Depth = 15;
    private const float Spacing = 40f;
    private static readonly ReadoutActor[] NoActors = [];

    [Theory]
    [InlineData(true, true, true)]
    [InlineData(true, false, false)]
    [InlineData(false, true, false)]
    [InlineData(false, false, false)]
    public void Visible_NeedsAnArmedLevelAndTheExplicitPreference(bool armed, bool enabled, bool expected)
    {
        Assert.Equal(expected, PositionReadout.Visible(armed, enabled));
    }

    [Fact]
    public void CoordinateVisibility_IsOffByDefaultAndExplicitlyToggleable()
    {
        var visibility = new CoordinateVisibility();
        Assert.False(visibility.Enabled);
        Assert.False(visibility.Visible(true, true));
        visibility.Toggle();
        Assert.True(visibility.Visible(true, true));
        visibility.Set(true);
        Assert.True(visibility.Enabled);
        Assert.False(visibility.Visible(false, true));
        Assert.False(visibility.Visible(true, false));
        Assert.True(visibility.Enabled);
        visibility.Toggle();
        Assert.False(visibility.Visible(true, true));
    }

    [Theory]
    [InlineData(true, true, false, false, true)]
    [InlineData(false, true, false, false, false)]
    [InlineData(true, false, false, false, false)]
    [InlineData(true, true, true, false, false)]
    [InlineData(true, true, false, true, false)]
    public void CoordinateHotkey_RequiresAnArmedLevelAndNoFocusedInput(bool armed, bool pressed, bool console, bool text, bool expected) =>
        Assert.Equal(expected, PositionReadout.ShouldToggle(armed, pressed, console, text));

    [Fact]
    public void CoordinateHotkey_IsIgnoredWhileTheModConsoleHasFocus() =>
        Assert.False(PositionReadout.ShouldToggle(true, true, false, false, modConsoleFocused: true));

    [Theory]
    [InlineData(-280f, -280f, 0, 0)]
    [InlineData(280f, 280f, 14, 14)]
    [InlineData(0f, 0f, 7, 7)]
    [InlineData(240f, 0f, 13, 7)]
    public void CellOf_CellCentre_ReturnsThatCell(float x, float z, int cellX, int cellZ)
    {
        var cell = PositionReadout.CellOf(x, z, Width, Depth, Spacing);

        Assert.Equal(new GridCell(cellX, cellZ, true), cell);
    }

    [Fact]
    public void CellOf_TileEdge_BelongsToTheTileAwayFromTheOrigin()
    {
        Assert.Equal(new GridCell(8, 7, true), PositionReadout.CellOf(20f, 0f, Width, Depth, Spacing));
        Assert.Equal(new GridCell(7, 7, true), PositionReadout.CellOf(19.9f, 0f, Width, Depth, Spacing));
        Assert.Equal(new GridCell(7, 7, true), PositionReadout.CellOf(-20f, 0f, Width, Depth, Spacing));
        Assert.Equal(new GridCell(6, 7, true), PositionReadout.CellOf(-20.1f, 0f, Width, Depth, Spacing));
    }

    [Fact]
    public void CellOf_OuterEdgeOfTheLastTile_IsStillInTheGrid()
    {
        Assert.Equal(new GridCell(14, 0, true), PositionReadout.CellOf(299.9f, -299.9f, Width, Depth, Spacing));
        Assert.Equal(new GridCell(0, 14, true), PositionReadout.CellOf(-299.9f, 299.9f, Width, Depth, Spacing));
    }

    [Theory]
    [InlineData(300f, 0f, 15, 7)]
    [InlineData(-300.1f, 0f, -1, 7)]
    [InlineData(0f, 340f, 7, 16)]
    [InlineData(0f, -1000f, 7, -18)]
    public void CellOf_OutsideTheGrid_ReturnsTheUnclampedCellAndFlagsIt(float x, float z, int cellX, int cellZ)
    {
        var cell = PositionReadout.CellOf(x, z, Width, Depth, Spacing);

        Assert.Equal(new GridCell(cellX, cellZ, false), cell);
    }

    [Fact]
    public void CellOf_EvenSizedGrid_CentresTheOriginBetweenTwoCells()
    {
        Assert.Equal(new GridCell(0, 0, true), PositionReadout.CellOf(-20f, -20f, 2, 2, Spacing));
        Assert.Equal(new GridCell(1, 1, true), PositionReadout.CellOf(20f, 20f, 2, 2, Spacing));
    }

    [Fact]
    public void LevelOf_RoundsToTheNearestHeightStep()
    {
        Assert.Equal(1, PositionReadout.LevelOf(22f, 20f));
        Assert.Equal(0, PositionReadout.LevelOf(9.9f, 20f));
        Assert.Equal(-2, PositionReadout.LevelOf(-41f, 20f));
    }

    // --- Render: on-screen block, columns sized to the data actually shown ---

    [Fact]
    public void Render_PlayerOnly_HasNoColumnsWiderThanTheLabelAndPosition()
    {
        var text = PositionReadout.Render(120f, 2f, 3f, -72f, NoActors);

        Assert.Equal("me: pos(120, 2, 3) floor -72", text);
    }

    [Fact]
    public void Render_PlayerBelowTheFloor_AppendsTheFlag()
    {
        var text = PositionReadout.Render(0f, -80f, 0f, -72f, NoActors);

        Assert.EndsWith("BELOW FLOOR", text);
    }

    [Fact]
    public void Render_PlayerAtTheFloor_IsNotBelow()
    {
        var text = PositionReadout.Render(0f, -72f, 0f, -72f, NoActors);

        Assert.DoesNotContain("BELOW", text);
    }

    [Fact]
    public void Render_NoFloor_OmitsTheFloorAndNeverFlags()
    {
        var text = PositionReadout.Render(0f, -5000f, 0f, float.NegativeInfinity, NoActors);

        Assert.DoesNotContain("floor", text);
        Assert.DoesNotContain("BELOW", text);
    }

    [Fact]
    public void Render_NeverPrintsNegativeZero()
    {
        var text = PositionReadout.Render(-0.2f, 1.5f, -0.4f, -72f, NoActors);

        Assert.Equal("me: pos(0, 2, 0) floor -72", text);
    }

    [Fact]
    public void Render_OneShortActor_IdColumnFloorsToThreeDigitsSoLaterIdsDoNotShiftIt()
    {
        var actors = new[] { new ReadoutActor("enemy:", 4, 125f, 2f, -10f) };

        var text = PositionReadout.Render(120f, 2f, 3f, -72f, actors);

        Assert.Equal(
            "me:        pos(120, 2,   3) floor -72\n" +
            "enemy: 4   pos(125, 2, -10)",
            text);
    }

    [Fact]
    public void Render_IdBeyondThreeDigits_WidensTheColumn()
    {
        var actors = new[] { new ReadoutActor("enemy:", 12345, 0f, 0f, 0f) };

        var text = PositionReadout.Render(0f, 0f, 0f, -72f, actors);
        var actorLine = text.Split('\n')[1];

        Assert.StartsWith("enemy: 12345 ", actorLine);
    }

    [Fact]
    public void Render_ActorBelowTheFloor_AppendsTheFlag()
    {
        var actors = new[] { new ReadoutActor("enemy:", 4, 125f, -80f, -10f) };

        var text = PositionReadout.Render(0f, 0f, 0f, -72f, actors);

        Assert.EndsWith("BELOW FLOOR", text);
    }

    [Fact]
    public void Render_NoFloor_ActorNeverFlags()
    {
        var actors = new[] { new ReadoutActor("boss:", 5, 0f, -5000f, 0f) };

        var text = PositionReadout.Render(0f, 0f, 0f, float.NegativeInfinity, actors);

        Assert.DoesNotContain("BELOW", text);
    }

    [Fact]
    public void Render_LongerLabelOrIdWidensTheColumnForEveryLine()
    {
        var actors = new[] { new ReadoutActor("final boss:", 12345, 1f, 1f, 1f) };

        var text = PositionReadout.Render(1f, 1f, 1f, -72f, actors);

        var lines = text.Split('\n');
        var meLine = lines[0];
        var actorLine = lines[1];

        // Both lines' pos columns start at the same index once the longer label/id widen the shared columns.
        Assert.Equal(meLine.IndexOf("pos(", System.StringComparison.Ordinal), actorLine.IndexOf("pos(", System.StringComparison.Ordinal));
        Assert.StartsWith("final boss: 12345 ", actorLine);
    }

    [Fact]
    public void Render_WithTypeName_AppendsItRightAfterThePosition()
    {
        var actors = new[] { new ReadoutActor("miniboss:", 41, -80f, 22f, 200f, "MinibossGolem") };

        var text = PositionReadout.Render(0f, 0f, 0f, -72f, actors);

        Assert.Equal(
            "me:           pos(  0,  0,   0) floor -72\n" +
            "miniboss: 41  pos(-80, 22, 200) MinibossGolem",
            text);
    }

    [Fact]
    public void Render_BelowFloorWithTypeName_FlagComesBeforeTheTypeName()
    {
        var actors = new[] { new ReadoutActor("miniboss:", 41, 0f, -80f, 0f, "MinibossGolem") };

        var text = PositionReadout.Render(0f, 0f, 0f, -72f, actors);
        var actorLine = text.Split('\n')[1];

        Assert.EndsWith("BELOW FLOOR MinibossGolem", actorLine);
    }

    [Fact]
    public void Render_TypeNameOnOneRowOnly_OtherRowsCarryNoFlagPadding()
    {
        var actors = new[]
        {
            new ReadoutActor("miniboss:", 41, 0f, 0f, 0f, "MinibossGolem"),
            new ReadoutActor("enemy:", 4, 0f, 0f, 0f),
        };

        var text = PositionReadout.Render(0f, 0f, 0f, -72f, actors);
        var lines = text.Split('\n');

        Assert.EndsWith("MinibossGolem", lines[1]);
        Assert.EndsWith("pos(0, 0, 0)", lines[2]);
    }

    [Fact]
    public void Render_NoActorHasATypeName_FlagColumnCarriesNoReservedPadding()
    {
        var actors = new[] { new ReadoutActor("enemy:", 4, 0f, 0f, 0f) };

        var text = PositionReadout.Render(0f, 0f, 0f, -72f, actors);
        var actorLine = text.Split('\n')[1];

        Assert.Equal("enemy: 4   pos(0, 0, 0)", actorLine);
    }

    // --- Cell-change log lines (harness-gated, off screen) ---

    [Fact]
    public void FormatCellLog_ShowsNameCellLevelAndPosition()
    {
        var text = PositionReadout.FormatCellLog("me", 240f, 22f, 0f, new GridCell(13, 7, true), 1);

        Assert.Equal("me cell (13,7) h1 pos (240, 22, 0)", text);
    }

    [Fact]
    public void FormatCellLog_OutsideTheGrid_MarksTheCell()
    {
        var text = PositionReadout.FormatCellLog("miniboss 41", -320f, 22f, 0f, new GridCell(-1, 7, false), 1);

        Assert.Equal("miniboss 41 cell (-1,7) outside h1 pos (-320, 22, 0)", text);
    }

    [Fact]
    public void FormatCellLog_NeverPrintsNegativeZero()
    {
        var text = PositionReadout.FormatCellLog("me", -0.2f, 1.5f, -0.4f, new GridCell(7, 7, true), 0);

        Assert.Contains("pos (0, 2, 0)", text);
    }
}
