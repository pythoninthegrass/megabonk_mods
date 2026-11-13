namespace MegabonkLevels.Tests;

public class RunExclusionTests
{
    private const int Calcium = 0;
    private const int LastStock = 20;

    [Fact]
    public void Reason_StockCharacterOnStockLevel_IsNotExcluded()
    {
        Assert.Null(RunExclusion.Reason(false, Calcium));
        Assert.Null(RunExclusion.Reason(false, LastStock));
    }

    [Fact]
    public void Reason_NoCharacterYetOnStockLevel_IsNotExcluded()
    {
        Assert.Null(RunExclusion.Reason(false, null));
    }

    [Fact]
    public void Reason_SqueakerOnStockLevel_IsExcluded()
    {
        Assert.Equal(RunExclusion.ModCharacterReason, RunExclusion.Reason(false, SqueakerCharacter.Id));
    }

    [Fact]
    public void Reason_StockCharacterOnCustomLevel_IsExcluded()
    {
        Assert.Equal(RunExclusion.CustomLevelReason, RunExclusion.Reason(true, Calcium));
    }

    [Fact]
    public void Reason_NoCharacterYetOnCustomLevel_IsExcluded()
    {
        Assert.Equal(RunExclusion.CustomLevelReason, RunExclusion.Reason(true, null));
    }

    [Fact]
    public void Reason_SqueakerOnCustomLevel_IsExcluded()
    {
        Assert.NotNull(RunExclusion.Reason(true, SqueakerCharacter.Id));
    }
}
