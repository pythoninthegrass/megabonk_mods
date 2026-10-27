namespace MegabonkLevels.Tests;

public class RealInputDiagnosticTests
{
    [Fact]
    public void Describe_NoInput_ReturnsNull()
    {
        Assert.Null(RealInputDiagnostic.Describe("", false, false, true));
    }

    [Fact]
    public void Describe_Text_ReportsTextAndCharCodes()
    {
        var line = RealInputDiagnostic.Describe("ab", false, false, true);

        Assert.NotNull(line);
        Assert.Contains("inputString=\"ab\"", line);
        Assert.Contains("codes=97 98", line);
    }

    [Fact]
    public void Describe_ControlCharacters_AreEscaped()
    {
        var line = RealInputDiagnostic.Describe("\b\r\n", false, false, true);

        Assert.NotNull(line);
        Assert.Contains("inputString=\"\\b\\r\\n\"", line);
        Assert.Contains("codes=8 13 10", line);
        Assert.DoesNotContain('\b', line);
        Assert.DoesNotContain('\r', line);
        Assert.DoesNotContain('\n', line);
    }

    [Fact]
    public void Describe_BackspaceKeyDownWithoutText_IsReported()
    {
        var line = RealInputDiagnostic.Describe("", true, false, true);

        Assert.NotNull(line);
        Assert.Contains("Backspace down", line);
        Assert.DoesNotContain("inputString", line);
    }

    [Fact]
    public void Describe_ReturnKeyDownWithoutText_IsReported()
    {
        var line = RealInputDiagnostic.Describe("", false, true, true);

        Assert.NotNull(line);
        Assert.Contains("Return down", line);
    }

    [Theory]
    [InlineData(true, "focused=true")]
    [InlineData(false, "focused=false")]
    public void Describe_ReportsFieldFocus(bool focused, string expected)
    {
        var line = RealInputDiagnostic.Describe("a", false, false, focused);

        Assert.Contains(expected, line);
    }
}
