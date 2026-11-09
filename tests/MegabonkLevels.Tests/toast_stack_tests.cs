namespace MegabonkLevels.Tests;

public class ToastStackTests
{
    [Fact]
    public void Push_PlacesNewestFirst()
    {
        var stack = new ToastStack(3f, 5);
        stack.Push("a", false, 0f);
        stack.Push("b", true, 1f);

        Assert.Equal(new[] { "b", "a" }, stack.Items.Select(t => t.Text));
        Assert.True(stack.Items[0].IsError);
        Assert.False(stack.Items[1].IsError);
    }

    [Fact]
    public void Expire_RemovesOnlyToastsPastTheirLifetime()
    {
        var stack = new ToastStack(3f, 5);
        stack.Push("a", false, 0f);
        stack.Push("b", false, 2f);

        Assert.True(stack.Expire(3f));

        Assert.Equal(new[] { "b" }, stack.Items.Select(t => t.Text));
    }

    [Fact]
    public void Expire_NothingDue_ReportsNoChange()
    {
        var stack = new ToastStack(3f, 5);
        stack.Push("a", false, 0f);

        Assert.False(stack.Expire(2.9f));
        Assert.Single(stack.Items);
    }

    [Fact]
    public void Push_PastTheCap_DropsTheOldest()
    {
        var stack = new ToastStack(3f, 2);
        stack.Push("a", false, 0f);
        stack.Push("b", false, 0f);
        stack.Push("c", false, 0f);

        Assert.Equal(new[] { "c", "b" }, stack.Items.Select(t => t.Text));
    }

    [Fact]
    public void Dismiss_RemovesTheToastAtTheIndex()
    {
        var stack = new ToastStack(3f, 5);
        stack.Push("a", false, 0f);
        stack.Push("b", false, 0f);
        stack.Push("c", false, 0f);

        stack.Dismiss(1);

        Assert.Equal(new[] { "c", "a" }, stack.Items.Select(t => t.Text));
    }

    [Fact]
    public void Dismiss_OutOfRange_IsIgnored()
    {
        var stack = new ToastStack(3f, 5);
        stack.Push("a", false, 0f);

        stack.Dismiss(4);
        stack.Dismiss(-1);

        Assert.Single(stack.Items);
    }
}
