namespace MegabonkLevels.Tests;

public class CustomLevelStateTests
{
    [Fact]
    public void MarkEditorUsed_ImmediatelyGuardsCurrentNormalRun()
    {
        CustomLevelState.Reset();
        CustomLevelState.OnRunStarting();
        CustomLevelState.MarkEditorUsed();
        Assert.True(CustomLevelState.IsActive);
        CustomLevelState.MarkEditorUsed();
        Assert.True(CustomLevelState.IsActive);
    }

    [Fact]
    public void MarkEditorUsed_DoesNotMarkNextNormalRun()
    {
        CustomLevelState.Reset();
        CustomLevelState.MarkEditorUsed();
        CustomLevelState.OnRunStarting();
        Assert.False(CustomLevelState.IsActive);
    }

    [Fact]
    public void OnRunStarting_WithNoPendingStart_StaysInactive()
    {
        CustomLevelState.Reset();

        CustomLevelState.OnRunStarting();

        Assert.False(CustomLevelState.IsActive);
    }

    [Fact]
    public void OnRunStarting_AfterMarkPendingStart_BecomesActive()
    {
        CustomLevelState.Reset();

        CustomLevelState.MarkPendingStart();
        CustomLevelState.OnRunStarting();

        Assert.True(CustomLevelState.IsActive);
    }

    [Fact]
    public void OnRunStarting_ConsumesPendingStart_SoTheNextRunIsNotActive()
    {
        CustomLevelState.Reset();

        CustomLevelState.MarkPendingStart();
        CustomLevelState.OnRunStarting();
        CustomLevelState.OnRunStarting();

        Assert.False(CustomLevelState.IsActive);
    }

    [Fact]
    public void OnRunStarting_AfterACustomRun_ANormalRunIsNotActive()
    {
        CustomLevelState.Reset();

        CustomLevelState.MarkPendingStart();
        CustomLevelState.OnRunStarting();
        Assert.True(CustomLevelState.IsActive);

        CustomLevelState.OnRunStarting();

        Assert.False(CustomLevelState.IsActive);
    }
}
