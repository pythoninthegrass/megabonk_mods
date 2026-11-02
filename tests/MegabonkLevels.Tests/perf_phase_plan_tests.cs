using MegabonkLevels;
using Xunit;

public class PerfPhasePlanTests
{
    private static PerfPhasePlan.Node Node(string name, params PerfPhasePlan.Node[] subs)
    {
        var node = new PerfPhasePlan.Node { Name = name };
        node.SubSystems.AddRange(subs);
        return node;
    }

    [Fact]
    public void Paths_walks_depth_first_with_dotted_names()
    {
        var roots = new List<PerfPhasePlan.Node>
        {
            Node("EarlyUpdate"),
            Node("FixedUpdate", Node("ScriptRunBehaviourUpdate"), Node("PhysicsSimulation", Node("PhysicsUpdate"))),
            Node("Update"),
        };

        var paths = PerfPhasePlan.Paths(roots);

        Assert.Equal(
            new[]
            {
                "EarlyUpdate",
                "FixedUpdate",
                "FixedUpdate.ScriptRunBehaviourUpdate",
                "FixedUpdate.PhysicsSimulation",
                "FixedUpdate.PhysicsSimulation.PhysicsUpdate",
                "Update",
            },
            paths);
    }

    [Fact]
    public void Paths_of_an_empty_tree_is_empty()
    {
        Assert.Empty(PerfPhasePlan.Paths(new List<PerfPhasePlan.Node>()));
    }

    [Fact]
    public void Accumulate_totals_calls_and_keeps_the_max()
    {
        var slot = new PhaseSlot { Path = "Update" };

        PerfPhasePlan.Accumulate(slot, 2.5);
        PerfPhasePlan.Accumulate(slot, 7.0);
        PerfPhasePlan.Accumulate(slot, 1.0);

        Assert.Equal(3, slot.Calls);
        Assert.Equal(10.5, slot.TotalMs);
        Assert.Equal(7.0, slot.MaxMs);
    }

    [Fact]
    public void SelfMs_is_the_parent_total_beyond_its_children()
    {
        Assert.Equal(3.0, PerfPhasePlan.SelfMs(10.0, 7.0));
    }

    [Fact]
    public void SelfMs_never_goes_negative()
    {
        Assert.Equal(0.0, PerfPhasePlan.SelfMs(10.0, 12.0));
    }

    [Fact]
    public void GcPauseMsPerFrame_divides_the_window_delta_by_frames()
    {
        Assert.Equal(0.5, PerfPhasePlan.GcPauseMsPerFrame(50.0, 100));
    }

    [Fact]
    public void GcPauseMsPerFrame_is_zero_without_sampled_frames()
    {
        Assert.Equal(0.0, PerfPhasePlan.GcPauseMsPerFrame(50.0, 0));
    }
}
