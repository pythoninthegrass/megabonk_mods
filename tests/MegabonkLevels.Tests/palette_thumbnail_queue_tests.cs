namespace MegabonkLevels.Tests;

public class PaletteThumbnailQueueTests
{
    private static CatalogId Id(string segment) => CatalogId.Parse($"forest/{segment}");

    private static readonly CatalogId[] Ten = Enumerable.Range(0, 10).Select(i => Id($"shrines/{i}")).ToArray();

    [Fact]
    public void Step_RendersAtMostTheBudgetPerCall()
    {
        var queue = new PaletteThumbnailQueue(3);
        var asked = new List<CatalogId>();

        queue.Request(Ten);
        var first = queue.Step(id =>
        {
            asked.Add(id);
            return true;
        });
        var second = queue.Step(id =>
        {
            asked.Add(id);
            return true;
        });

        Assert.Equal(3, first);
        Assert.Equal(3, second);
        Assert.Equal(Ten.Take(6).ToArray(), asked);
        Assert.Equal(4, queue.PendingCount);
    }

    [Fact]
    public void Step_SkipsCachedIdsWithoutSpendingTheBudget()
    {
        var queue = new PaletteThumbnailQueue(2);
        var asked = new List<CatalogId>();

        queue.Request(Ten);
        var rendered = queue.Step(id =>
        {
            asked.Add(id);
            return false;
        });

        Assert.Equal(0, rendered);
        Assert.Equal(Ten, asked);
        Assert.True(queue.IsEmpty);
    }

    [Fact]
    public void Request_DeduplicatesAndStartsAgainAtTheFront()
    {
        var queue = new PaletteThumbnailQueue(1);
        var asked = new List<CatalogId>();
        bool Render(CatalogId id)
        {
            asked.Add(id);
            return true;
        }

        queue.Request([Ten[0], Ten[1], Ten[0]]);
        queue.Step(Render);
        queue.Step(Render);
        Assert.Equal([Ten[0], Ten[1]], asked);

        asked.Clear();
        queue.Request([Ten[5], Ten[0]]);
        Assert.Equal(2, queue.PendingCount);
        queue.Step(Render);
        Assert.Equal(Ten[5], Assert.Single(asked));
    }

    [Fact]
    public void IsEmpty_FalseWhileIdsRemainToAskFor()
    {
        var queue = new PaletteThumbnailQueue(1);

        Assert.True(queue.IsEmpty);
        queue.Request([Ten[0]]);
        Assert.False(queue.IsEmpty);
        queue.Step(_ => false);
        Assert.True(queue.IsEmpty);
    }

    [Fact]
    public void Step_WithoutBudget_LeavesTheQueuePending()
    {
        var queue = new PaletteThumbnailQueue(0);
        var asked = 0;

        queue.Request(Ten);

        Assert.Equal(0, queue.Step(_ =>
        {
            asked++;
            return true;
        }));
        Assert.Equal(0, asked);
        Assert.False(queue.IsEmpty);
    }
}
