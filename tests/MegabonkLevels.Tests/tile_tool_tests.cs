namespace MegabonkLevels.Tests;

public class TileToolTests
{
    private const int LowestLevel = -3;

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
        var op = TileTools.Build(TileTool.Raise, 4, 5, new TileState(2, SlopeDirection.East), LowestLevel);

        Assert.Equal(new SetTileHeight(4, 5, 3).ToEditOp(), op);
    }

    [Fact]
    public void Build_Lower_SetsHeightOneLower()
    {
        var op = TileTools.Build(TileTool.Lower, 4, 5, new TileState(2, SlopeDirection.None), LowestLevel);

        Assert.Equal(new SetTileHeight(4, 5, 1).ToEditOp(), op);
    }

    [Fact]
    public void Build_LowerAtTheLowestLevel_ReturnsNoOp()
    {
        Assert.Null(TileTools.Build(TileTool.Lower, 4, 5, new TileState(LowestLevel, SlopeDirection.None), LowestLevel));
    }

    [Fact]
    public void Build_LowerBelowZero_IsAllowedDownToTheLowestLevel()
    {
        var op = TileTools.Build(TileTool.Lower, 4, 5, new TileState(0, SlopeDirection.None), LowestLevel);

        Assert.Equal(new SetTileHeight(4, 5, -1).ToEditOp(), op);
    }

    [Fact]
    public void Build_Slope_SetsTheNextSlope()
    {
        var op = TileTools.Build(TileTool.Slope, 4, 5, new TileState(2, SlopeDirection.South), LowestLevel);

        Assert.Equal(new SetTileSlope(4, 5, SlopeDirection.West).ToEditOp(), op);
    }

    [Fact]
    public void Build_Remove_RemovesTheTile()
    {
        var op = TileTools.Build(TileTool.Remove, 4, 5, new TileState(2, SlopeDirection.None), LowestLevel);

        Assert.Equal(new RemoveTile(4, 5).ToEditOp(), op);
    }

    [Theory]
    [InlineData(1, TileTool.Raise)]
    [InlineData(2, TileTool.Lower)]
    [InlineData(3, TileTool.Slope)]
    [InlineData(4, TileTool.Remove)]
    public void FromHotkey_MapsDigitsOneToFour(int digit, TileTool expected)
    {
        Assert.Equal(expected, TileTools.FromHotkey(digit));
    }

    [Fact]
    public void ToolbarText_MarksTheCurrentToolAndDescribesTheTarget()
    {
        var text = TileTools.ToolbarText(TileTool.Slope, (9, 7, new TileState(1, SlopeDirection.East)));

        Assert.Equal("1 Raise   2 Lower   <color=#ffd84d>[3 Slope]</color>   4 Remove\ntarget (9,7) level 1 slope East", text);
    }

    [Fact]
    public void ToolbarText_NoTarget_SaysSo()
    {
        var text = TileTools.ToolbarText(TileTool.Raise, null);

        Assert.Equal("<color=#ffd84d>[1 Raise]</color>   2 Lower   3 Slope   4 Remove\ntarget none", text);
    }

    [Theory]
    [InlineData(0)]
    [InlineData(5)]
    public void FromHotkey_OtherDigits_ReturnNoTool(int digit)
    {
        Assert.Null(TileTools.FromHotkey(digit));
    }
}
