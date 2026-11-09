namespace MegabonkLevels.Tests;

public class MagnifierIconTests
{
    private const int Size = 24;

    [Fact]
    public void Mask_HasTheRequestedSize()
    {
        var mask = MagnifierIcon.Mask(Size);

        Assert.Equal(Size, mask.GetLength(0));
        Assert.Equal(Size, mask.GetLength(1));
    }

    [Fact]
    public void Mask_DrawsALensRingAroundAnEmptyCentre()
    {
        var mask = MagnifierIcon.Mask(Size);
        var lensCentre = Size * 2 / 5;

        Assert.False(mask[lensCentre, lensCentre]);
        Assert.True(mask[lensCentre, 0 + 3]);
    }

    [Fact]
    public void Mask_DrawsAHandleTowardsTheBottomRight()
    {
        var mask = MagnifierIcon.Mask(Size);

        Assert.True(mask[Size - 3, Size - 3]);
        Assert.False(mask[Size - 1, 0]);
        Assert.False(mask[0, Size - 1]);
    }
}
