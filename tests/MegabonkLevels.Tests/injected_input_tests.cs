namespace MegabonkLevels.Tests;

public class InjectedInputQueueTests
{
    private static readonly string[] NoModifiers = [];

    [Fact]
    public void Tap_WithoutModifiers_PressesOnFirstFrameAndReleasesOnTheNext()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueTap("R", NoModifiers);

        queue.BeginFrame(1);
        Assert.True(queue.WasKeyPressedThisFrame("R"));
        Assert.True(queue.IsKeyHeld("R"));
        Assert.False(queue.WasKeyReleasedThisFrame("R"));

        queue.BeginFrame(2);
        Assert.False(queue.WasKeyPressedThisFrame("R"));
        Assert.False(queue.IsKeyHeld("R"));
        Assert.True(queue.WasKeyReleasedThisFrame("R"));

        queue.BeginFrame(3);
        Assert.False(queue.WasKeyReleasedThisFrame("R"));
    }

    [Fact]
    public void Tap_WithModifiers_FollowsTheModifierKeyKeyModifierSchedule()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueTap("Z", ["LeftControl", "LeftShift"]);

        queue.BeginFrame(1);
        Assert.True(queue.WasKeyPressedThisFrame("LeftControl"));
        Assert.True(queue.WasKeyPressedThisFrame("LeftShift"));
        Assert.False(queue.IsKeyHeld("Z"));

        queue.BeginFrame(2);
        Assert.True(queue.WasKeyPressedThisFrame("Z"));
        Assert.True(queue.IsKeyHeld("LeftControl"));
        Assert.True(queue.IsKeyHeld("LeftShift"));

        queue.BeginFrame(3);
        Assert.True(queue.WasKeyReleasedThisFrame("Z"));
        Assert.True(queue.IsKeyHeld("LeftControl"));

        queue.BeginFrame(4);
        Assert.True(queue.WasKeyReleasedThisFrame("LeftControl"));
        Assert.True(queue.WasKeyReleasedThisFrame("LeftShift"));
        Assert.False(queue.IsKeyHeld("LeftControl"));
        Assert.False(queue.IsKeyHeld("LeftShift"));
    }

    [Fact]
    public void Tap_AfterAnotherTap_StartsWhenTheFirstEnds()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueTap("A", NoModifiers);
        queue.EnqueueTap("B", NoModifiers);

        queue.BeginFrame(1);
        Assert.True(queue.WasKeyPressedThisFrame("A"));
        Assert.False(queue.IsKeyHeld("B"));

        queue.BeginFrame(2);
        queue.BeginFrame(3);
        Assert.True(queue.WasKeyPressedThisFrame("B"));
    }

    [Fact]
    public void PressedAndReleased_LastExactlyOneFrame()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueKeyDown("W");

        queue.BeginFrame(1);
        Assert.True(queue.WasKeyPressedThisFrame("W"));

        queue.BeginFrame(2);
        Assert.False(queue.WasKeyPressedThisFrame("W"));

        queue.EnqueueKeyUp("W");
        queue.BeginFrame(3);
        Assert.True(queue.WasKeyReleasedThisFrame("W"));

        queue.BeginFrame(4);
        Assert.False(queue.WasKeyReleasedThisFrame("W"));
    }

    [Fact]
    public void Held_PersistsUntilKeyUp()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueKeyDown("W");

        for (var frame = 1; frame <= 20; frame++)
        {
            queue.BeginFrame(frame);
            Assert.True(queue.IsKeyHeld("W"));
        }

        queue.EnqueueKeyUp("W");
        queue.BeginFrame(21);
        Assert.False(queue.IsKeyHeld("W"));
    }

    [Fact]
    public void Click_PressesOnFirstFrameAndReleasesOnTheNext()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueClick(0);

        queue.BeginFrame(1);
        Assert.True(queue.WasMousePressedThisFrame(0));
        Assert.True(queue.IsMouseHeld(0));
        Assert.False(queue.WasMouseReleasedThisFrame(0));

        queue.BeginFrame(2);
        Assert.False(queue.WasMousePressedThisFrame(0));
        Assert.False(queue.IsMouseHeld(0));
        Assert.True(queue.WasMouseReleasedThisFrame(0));

        queue.BeginFrame(3);
        Assert.False(queue.WasMouseReleasedThisFrame(0));
    }

    [Fact]
    public void Click_AfterMouseMove_UsesTheMovedPositionOnTheSameFrame()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueMouseMove(120f, 340f);
        queue.EnqueueClick(0);

        queue.BeginFrame(1);

        Assert.Equal((120f, 340f), queue.MousePosition);
        Assert.True(queue.WasMousePressedThisFrame(0));
    }

    [Fact]
    public void MouseDownAndUp_HoldTheButtonBetween()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueMouseDown(1);

        queue.BeginFrame(1);
        queue.BeginFrame(2);
        queue.BeginFrame(3);
        Assert.True(queue.IsMouseHeld(1));

        queue.EnqueueMouseUp(1);
        queue.BeginFrame(4);
        Assert.False(queue.IsMouseHeld(1));
        Assert.True(queue.WasMouseReleasedThisFrame(1));
    }

    [Fact]
    public void Text_DeliversOneCharacterPerFrame()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueText("ab");

        queue.BeginFrame(1);
        Assert.Equal("a", queue.InputStringThisFrame);

        queue.BeginFrame(2);
        Assert.Equal("b", queue.InputStringThisFrame);

        queue.BeginFrame(3);
        Assert.Equal("", queue.InputStringThisFrame);
    }

    [Fact]
    public void Text_PassesBackspaceAndReturnThrough()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueText("a\b\n");

        queue.BeginFrame(1);
        Assert.Equal("a", queue.InputStringThisFrame);

        queue.BeginFrame(2);
        Assert.Equal("\b", queue.InputStringThisFrame);

        queue.BeginFrame(3);
        Assert.Equal("\n", queue.InputStringThisFrame);
    }

    [Fact]
    public void MousePosition_IsNullUntilAMoveIsQueued()
    {
        var queue = new InjectedInputQueue();

        queue.BeginFrame(1);

        Assert.Null(queue.MousePosition);
    }

    [Fact]
    public void MousePosition_ExpiresOneSecondAfterTheMove()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueMouseMove(10f, 20f);

        queue.BeginFrame(1, 5f);
        queue.BeginFrame(2, 5.9f);
        Assert.Equal((10f, 20f), queue.MousePosition);

        queue.BeginFrame(3, 6f);
        Assert.Null(queue.MousePosition);
    }

    [Fact]
    public void MousePosition_ANewMoveRestartsTheExpiry()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueMouseMove(10f, 20f);
        queue.BeginFrame(1, 5f);

        queue.EnqueueMouseMove(30f, 40f);
        queue.BeginFrame(2, 5.8f);
        queue.BeginFrame(3, 6.5f);

        Assert.Equal((30f, 40f), queue.MousePosition);
    }

    [Fact]
    public void MousePosition_PersistsUntilCleared()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueMouseMove(10f, 20f);

        queue.BeginFrame(1);
        queue.BeginFrame(2);
        queue.BeginFrame(3);
        Assert.Equal((10f, 20f), queue.MousePosition);

        queue.ClearMouse();
        Assert.Null(queue.MousePosition);

        queue.BeginFrame(4);
        Assert.Null(queue.MousePosition);
    }

    [Fact]
    public void BeginFrame_WithTheSameFrameNumber_IsANoOp()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueTap("R", NoModifiers);

        queue.BeginFrame(1);
        queue.BeginFrame(1);
        queue.BeginFrame(1);

        Assert.True(queue.WasKeyPressedThisFrame("R"));
        Assert.True(queue.IsKeyHeld("R"));

        queue.BeginFrame(2);
        Assert.True(queue.WasKeyReleasedThisFrame("R"));
    }

    [Fact]
    public void UnknownKeyName_StillQueues()
    {
        var queue = new InjectedInputQueue();
        queue.EnqueueTap("NotAKey", NoModifiers);

        queue.BeginFrame(1);

        Assert.True(queue.WasKeyPressedThisFrame("NotAKey"));
    }

    [Fact]
    public void Queries_ForKeysNeverQueued_AreFalse()
    {
        var queue = new InjectedInputQueue();

        queue.BeginFrame(1);

        Assert.False(queue.IsKeyHeld("R"));
        Assert.False(queue.WasKeyPressedThisFrame("R"));
        Assert.False(queue.WasKeyReleasedThisFrame("R"));
        Assert.False(queue.IsMouseHeld(0));
        Assert.Equal("", queue.InputStringThisFrame);
    }
}
