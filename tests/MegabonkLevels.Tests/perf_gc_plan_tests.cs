using MegabonkLevels;
using Xunit;

public class PerfGcPlanTests
{
    [Fact]
    public void GcPauseMsPerFrame_divides_the_window_delta_by_frames()
    {
        Assert.Equal(0.5, PerfGcPlan.GcPauseMsPerFrame(50.0, 100));
    }

    [Fact]
    public void GcPauseMsPerFrame_is_zero_without_sampled_frames()
    {
        Assert.Equal(0.0, PerfGcPlan.GcPauseMsPerFrame(50.0, 0));
    }
}
