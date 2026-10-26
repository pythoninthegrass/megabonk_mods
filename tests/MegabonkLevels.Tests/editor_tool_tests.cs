namespace MegabonkLevels.Tests;

public class EditorToolTests
{
    private const int LowestLevel = -3;

    [Fact]
    public void Build_ObjectTools_HaveNoTileOp()
    {
        Assert.Throws<ArgumentException>(() => TileTools.Build(EditorTool.Place, 4, 5, new TileState(2, SlopeDirection.None), LowestLevel));
    }

    [Theory]
    [InlineData(SlopeDirection.None, SlopeDirection.North)]
    [InlineData(SlopeDirection.North, SlopeDirection.East)]
    [InlineData(SlopeDirection.East, SlopeDirection.South)]
    [InlineData(SlopeDirection.South, SlopeDirection.West)]
    [InlineData(SlopeDirection.West, SlopeDirection.None)]
    public void NextSlope_TurnsClockwiseThroughFlat(SlopeDirection current, SlopeDirection expected)
    {
        Assert.Equal(expected, TileTools.NextSlope(current));
    }

    [Fact]
    public void Build_Raise_SetsHeightOneHigher()
    {
        var op = TileTools.Build(EditorTool.Raise, 4, 5, new TileState(2, SlopeDirection.East), LowestLevel);

        Assert.Equal(new SetTileHeight(4, 5, 3).ToEditOp(), op);
    }

    [Fact]
    public void Build_Lower_SetsHeightOneLower()
    {
        var op = TileTools.Build(EditorTool.Lower, 4, 5, new TileState(2, SlopeDirection.None), LowestLevel);

        Assert.Equal(new SetTileHeight(4, 5, 1).ToEditOp(), op);
    }

    [Fact]
    public void Build_LowerAtTheLowestLevel_ReturnsNoOp()
    {
        Assert.Null(TileTools.Build(EditorTool.Lower, 4, 5, new TileState(LowestLevel, SlopeDirection.None), LowestLevel));
    }

    [Fact]
    public void Build_LowerBelowZero_IsAllowedDownToTheLowestLevel()
    {
        var op = TileTools.Build(EditorTool.Lower, 4, 5, new TileState(0, SlopeDirection.None), LowestLevel);

        Assert.Equal(new SetTileHeight(4, 5, -1).ToEditOp(), op);
    }

    [Fact]
    public void Build_Slope_SetsTheNextSlope()
    {
        var op = TileTools.Build(EditorTool.Slope, 4, 5, new TileState(2, SlopeDirection.South), LowestLevel);

        Assert.Equal(new SetTileSlope(4, 5, SlopeDirection.West).ToEditOp(), op);
    }

    [Fact]
    public void Build_Remove_RemovesTheTile()
    {
        var op = TileTools.Build(EditorTool.Remove, 4, 5, new TileState(2, SlopeDirection.None), LowestLevel);

        Assert.Equal(new RemoveTile(4, 5).ToEditOp(), op);
    }

    [Fact]
    public void Default_IsSelect_SoTheFirstClickCannotEditATile()
    {
        Assert.Equal(EditorTool.Select, EditorTools.Default);
    }

    [Theory]
    [InlineData(1, EditorTool.Raise)]
    [InlineData(2, EditorTool.Lower)]
    [InlineData(3, EditorTool.Slope)]
    [InlineData(4, EditorTool.Remove)]
    [InlineData(5, EditorTool.Place)]
    [InlineData(6, EditorTool.Select)]
    public void FromHotkey_MapsDigitsOneToSix(int digit, EditorTool expected)
    {
        Assert.Equal(expected, EditorTools.FromHotkey(digit));
    }

    [Fact]
    public void ToolbarText_MarksTheCurrentTool()
    {
        var text = EditorTools.ToolbarText(EditorTool.Slope);

        Assert.Equal("1 Raise   2 Lower   <color=#ffd84d>[3 Slope]</color>   4 Remove   5 Place   6 Select", text);
    }

    [Fact]
    public void ToolLabel_MarksOnlyTheCurrentTool()
    {
        Assert.Equal("<color=#ffd84d>[3 Slope]</color>", EditorTools.ToolLabel(EditorTool.Slope, EditorTool.Slope));
        Assert.Equal("4 Remove", EditorTools.ToolLabel(EditorTool.Remove, EditorTool.Slope));
    }

    [Theory]
    [InlineData(EditorTool.Raise, "Click a tile to raise it one level")]
    [InlineData(EditorTool.Lower, "Click a tile to lower it one level")]
    [InlineData(EditorTool.Slope, "Click a tile to cycle its slope: north, east, south, west, flat")]
    [InlineData(EditorTool.Remove, "Click a tile to remove it")]
    [InlineData(EditorTool.Place, "Pick an item in the palette, then click the map to place it")]
    [InlineData(EditorTool.Select, "Click an object to select it; drag to move, R rotate, Del remove")]
    public void Description_ExplainsEachTool(EditorTool tool, string expected) =>
        Assert.Equal(expected, EditorTools.Description(tool));

    [Fact]
    public void TileDetail_DescribesTheTarget()
    {
        Assert.Equal("target (9,7) level 1 slope East", EditorTools.TileDetail((9, 7, new TileState(1, SlopeDirection.East))));
    }

    [Fact]
    public void TileDetail_NoTarget_SaysSo()
    {
        Assert.Equal("target none", EditorTools.TileDetail(null));
    }

    [Fact]
    public void PlaceDetail_NothingSelected_PromptsForAPaletteEntry()
    {
        Assert.Equal("place (3,4) - pick an item in the palette", EditorTools.PlaceDetail((3, 4), null));
    }

    [Fact]
    public void PlaceDetail_ShowsTheCellAndTheSelectedItem()
    {
        Assert.Equal("place Chest at (3,4)", EditorTools.PlaceDetail((3, 4), "Chest"));
    }

    [Fact]
    public void PlaceDetail_NoCell_SaysNoTarget()
    {
        Assert.Equal("place Chest - target none", EditorTools.PlaceDetail(null, "Chest"));
    }

    [Fact]
    public void SelectDetail_ShowsTheSelectionAndTheTargetCell()
    {
        Assert.Equal("selected Tree0 - drag to move, R rotate, Del remove\ntarget (3,4)", EditorTools.SelectDetail("Tree0", null, (3, 4)));
    }

    [Fact]
    public void SelectDetail_NothingSelected_ShowsTheHoveredObject()
    {
        Assert.Equal("click to select Tree0", EditorTools.SelectDetail(null, "Tree0", (3, 4)));
    }

    [Fact]
    public void SelectDetail_NothingSelectedOrHovered_PromptsToClickAnObject()
    {
        Assert.Equal("click an object to select it", EditorTools.SelectDetail(null, null, null));
    }

    [Theory]
    [InlineData(0)]
    [InlineData(7)]
    public void FromHotkey_OtherDigits_ReturnNoTool(int digit)
    {
        Assert.Null(EditorTools.FromHotkey(digit));
    }
}
