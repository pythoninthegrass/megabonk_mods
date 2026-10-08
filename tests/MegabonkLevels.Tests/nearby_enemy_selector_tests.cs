namespace MegabonkLevels.Tests;

public class NearbyEnemySelectorTests
{
    private const float Floor = -72f;

    private static List<uint> Run(NearbyEnemySelector selector, params ActorPosition[] actors)
    {
        selector.Begin(0f, 0f, Floor);
        foreach (var actor in actors)
        {
            selector.Offer(actor);
        }

        var ids = new List<uint>();
        for (var i = 0; i < selector.Count; i++)
        {
            ids.Add(selector[i].Id);
        }

        return ids;
    }

    [Fact]
    public void Select_OrdersByHorizontalDistanceToThePlayer()
    {
        var ids = Run(new NearbyEnemySelector(5),
            new ActorPosition(1, 30f, 0f, 0f),
            new ActorPosition(2, 10f, 0f, 0f),
            new ActorPosition(3, 0f, 0f, 20f));

        Assert.Equal(new uint[] { 2, 3, 1 }, ids);
    }

    [Fact]
    public void Select_IgnoresHeightWhenMeasuringDistance()
    {
        var ids = Run(new NearbyEnemySelector(5),
            new ActorPosition(1, 20f, 0f, 0f),
            new ActorPosition(2, 30f, 0f, 0f),
            new ActorPosition(3, 10f, 500f, 0f));

        Assert.Equal(new uint[] { 3, 1, 2 }, ids);
    }

    [Fact]
    public void Select_PutsEnemiesBelowTheFloorBeforeNearerOnes()
    {
        var ids = Run(new NearbyEnemySelector(5),
            new ActorPosition(1, 5f, 0f, 0f),
            new ActorPosition(2, 200f, -80f, 0f),
            new ActorPosition(3, 100f, -90f, 0f));

        Assert.Equal(new uint[] { 3, 2, 1 }, ids);
    }

    [Fact]
    public void Select_EnemyExactlyAtTheFloorIsNotBelow()
    {
        var ids = Run(new NearbyEnemySelector(5),
            new ActorPosition(1, 5f, 0f, 0f),
            new ActorPosition(2, 200f, Floor, 0f));

        Assert.Equal(new uint[] { 1, 2 }, ids);
    }

    [Fact]
    public void Select_KeepsOnlyTheCapacityBestOfHundredsOfEnemies()
    {
        var selector = new NearbyEnemySelector(5);
        selector.Begin(0f, 0f, Floor);
        for (uint id = 1; id <= 400; id++)
        {
            selector.Offer(new ActorPosition(id, (401 - id) * 2f, 0f, 0f));
        }

        selector.Offer(new ActorPosition(9000, 1000f, -100f, 0f));

        Assert.Equal(5, selector.Count);
        Assert.Equal(9000u, selector[0].Id);
        Assert.Equal(new uint[] { 400, 399, 398, 397 }, Enumerable.Range(1, 4).Select(i => selector[i].Id).ToArray());
    }

    [Fact]
    public void Select_BreaksTiesByLowerId()
    {
        var ids = Run(new NearbyEnemySelector(5),
            new ActorPosition(7, 10f, 0f, 0f),
            new ActorPosition(3, 0f, 0f, 10f),
            new ActorPosition(5, -10f, 0f, 0f));

        Assert.Equal(new uint[] { 3, 5, 7 }, ids);
    }

    [Fact]
    public void Select_FewerEnemiesThanCapacity_ReturnsThemAll()
    {
        var ids = Run(new NearbyEnemySelector(5), new ActorPosition(1, 1f, 0f, 0f));

        Assert.Equal(new uint[] { 1 }, ids);
    }

    [Fact]
    public void Select_NoEnemies_IsEmpty()
    {
        Assert.Empty(Run(new NearbyEnemySelector(5)));
    }

    [Fact]
    public void Begin_ClearsThePreviousSelection()
    {
        var selector = new NearbyEnemySelector(5);
        Run(selector, new ActorPosition(1, 1f, 0f, 0f));

        selector.Begin(0f, 0f, Floor);

        Assert.Equal(0, selector.Count);
    }

    [Fact]
    public void Begin_MeasuresDistanceFromTheGivenPlayerPosition()
    {
        var selector = new NearbyEnemySelector(2);
        selector.Begin(100f, 100f, Floor);
        selector.Offer(new ActorPosition(1, 0f, 0f, 0f));
        selector.Offer(new ActorPosition(2, 90f, 0f, 90f));

        Assert.Equal(2u, selector[0].Id);
        Assert.Equal(1u, selector[1].Id);
    }
}
