namespace MegabonkLevels.Tests;

public class LevelStateTests
{
    [Fact]
    public void FromTiles_HoldsEveryGivenTile()
    {
        var state = LevelState.FromTiles(new Dictionary<(int X, int Z), TileState>
        {
            [(0, 0)] = new TileState(0, SlopeDirection.None),
            [(1, 0)] = new TileState(2, SlopeDirection.East),
        });

        Assert.Equal(2, state.Tiles.Count);
        Assert.Equal(new TileState(2, SlopeDirection.East), state.GetTile(1, 0));
        Assert.Empty(state.Objects);
    }

    [Fact]
    public void FromTiles_CopyIsIndependentOfTheSource()
    {
        var source = LevelState.FromTiles(new Dictionary<(int X, int Z), TileState> { [(0, 0)] = new TileState(1, SlopeDirection.None) });

        var copy = LevelState.FromTiles(source.Tiles);
        new EditStack(copy).Apply(new RemoveTile(0, 0).ToEditOp());

        Assert.Null(copy.GetTile(0, 0));
        Assert.Equal(new TileState(1, SlopeDirection.None), source.GetTile(0, 0));
    }
}
