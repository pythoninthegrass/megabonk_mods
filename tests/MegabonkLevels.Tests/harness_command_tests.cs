namespace MegabonkLevels.Tests;

public class HarnessCommandTests
{
    [Fact]
    public void TryParse_LoadLevel_ReturnsKindAndPath()
    {
        var ok = HarnessCommand.TryParse("""{"command":"load-level","path":"/tmp/a.mblevel.json"}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.LoadLevel, command.Kind);
        Assert.Equal("/tmp/a.mblevel.json", command.Path);
    }

    [Fact]
    public void TryParse_Screenshot_ReturnsKindAndPath()
    {
        var ok = HarnessCommand.TryParse("""{"command":"screenshot","path":"C:\\shots\\one.png"}""", out var command, out _);

        Assert.True(ok);
        Assert.Equal(HarnessCommandKind.Screenshot, command.Kind);
        Assert.Equal("C:\\shots\\one.png", command.Path);
    }

    [Fact]
    public void TryParse_LoadBundle_ReturnsKindAndPath()
    {
        var ok = HarnessCommand.TryParse("""{"command":"load-bundle","path":"C:\\packs\\testprop"}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.LoadBundle, command.Kind);
        Assert.Equal("C:\\packs\\testprop", command.Path);
        Assert.Equal("load-bundle", command.Name);
    }

    [Fact]
    public void TryParse_ShaderReport_ReturnsKind()
    {
        var ok = HarnessCommand.TryParse("""{"command":"shader-report"}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.ShaderReport, command.Kind);
        Assert.Equal("shader-report", command.Name);
    }

    [Theory]
    [InlineData("""{"command":"state"}""", "state")]
    [InlineData("""{"command":"load-level","path":"a"}""", "load-level")]
    [InlineData("""{"command":"editor","enabled":true}""", "editor")]
    [InlineData("""{"command":"camera","position":[1,2,3],"rotation":[4,5,6]}""", "camera")]
    public void TryParse_RecordsTheWireName(string json, string expected)
    {
        Assert.True(HarnessCommand.TryParse(json, out var command, out _));
        Assert.Equal(expected, command.Name);
    }

    [Fact]
    public void TryParse_Quit_NeedsNoPath()
    {
        var ok = HarnessCommand.TryParse("""{"command":"quit"}""", out var command, out _);

        Assert.True(ok);
        Assert.Equal(HarnessCommandKind.Quit, command.Kind);
        Assert.Null(command.Path);
    }

    [Theory]
    [InlineData("freeze", HarnessCommandKind.Freeze)]
    [InlineData("resume", HarnessCommandKind.Resume)]
    [InlineData("camera-clear", HarnessCommandKind.CameraClear)]
    [InlineData("invulnerable", HarnessCommandKind.Invulnerable)]
    [InlineData("vulnerable", HarnessCommandKind.Vulnerable)]
    [InlineData("steam-ready", HarnessCommandKind.SteamReady)]
    [InlineData("state", HarnessCommandKind.State)]
    public void TryParse_ArglessCommands_NeedNoPath(string name, HarnessCommandKind expected)
    {
        var ok = HarnessCommand.TryParse($$"""{"command":"{{name}}"}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(expected, command.Kind);
        Assert.Null(command.Path);
    }

    [Theory]
    [InlineData("true", true)]
    [InlineData("false", false)]
    public void TryParse_Editor_ReadsTheEnabledFlag(string enabled, bool expected)
    {
        var ok = HarnessCommand.TryParse($$"""{"command":"editor","enabled":{{enabled}}}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.Editor, command.Kind);
        Assert.Equal(expected, command.Enabled);
        Assert.Null(command.Path);
    }

    [Theory]
    [InlineData("""{"command":"editor"}""")]
    [InlineData("""{"command":"editor","enabled":"yes"}""")]
    [InlineData("""{"command":"editor","enabled":null}""")]
    public void TryParse_Editor_MissingOrNonBooleanEnabled_IsRejected(string json)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains("enabled", error);
    }

    [Theory]
    [InlineData("true", true)]
    [InlineData("false", false)]
    public void TryParse_Heartbeat_ReadsTheEnabledFlag(string enabled, bool expected)
    {
        var ok = HarnessCommand.TryParse($$"""{"command":"heartbeat","enabled":{{enabled}}}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.Heartbeat, command.Kind);
        Assert.Equal(expected, command.Enabled);
        Assert.Null(command.Path);
    }

    [Theory]
    [InlineData("""{"command":"heartbeat"}""")]
    [InlineData("""{"command":"heartbeat","enabled":"yes"}""")]
    [InlineData("""{"command":"heartbeat","enabled":1}""")]
    [InlineData("""{"command":"heartbeat","enabled":null}""")]
    public void TryParse_Heartbeat_MissingOrNonBooleanEnabled_IsRejected(string json)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains("enabled", error);
    }

    [Theory]
    [InlineData("true", true)]
    [InlineData("false", false)]
    public void TryParse_Cells_ReadsTheEnabledFlag(string enabled, bool expected)
    {
        var ok = HarnessCommand.TryParse($$"""{"command":"cells","enabled":{{enabled}}}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.Cells, command.Kind);
        Assert.Equal(expected, command.Enabled);
        Assert.Null(command.Path);
    }

    [Theory]
    [InlineData("""{"command":"cells"}""")]
    [InlineData("""{"command":"cells","enabled":"yes"}""")]
    [InlineData("""{"command":"cells","enabled":1}""")]
    [InlineData("""{"command":"cells","enabled":null}""")]
    public void TryParse_Cells_MissingOrNonBooleanEnabled_IsRejected(string json)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains("enabled", error);
    }

    [Fact]
    public void TryParse_Camera_ReturnsPositionAndEulerRotation()
    {
        var ok = HarnessCommand.TryParse("""{"command":"camera","position":[1.5,200,-3],"rotation":[90,0,45.5]}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.Camera, command.Kind);
        Assert.Equal(new CameraPose(1.5f, 200f, -3f, 90f, 0f, 45.5f), command.Pose);
    }

    [Theory]
    [InlineData("""{"command":"camera"}""", "position")]
    [InlineData("""{"command":"camera","position":[1,2,3]}""", "rotation")]
    [InlineData("""{"command":"camera","position":[1,2],"rotation":[0,0,0]}""", "position")]
    [InlineData("""{"command":"camera","position":[1,2,3],"rotation":[0,0,0,0]}""", "rotation")]
    [InlineData("""{"command":"camera","position":[1,"a",3],"rotation":[0,0,0]}""", "position")]
    [InlineData("""{"command":"camera","position":"1,2,3","rotation":[0,0,0]}""", "position")]
    public void TryParse_CameraWithoutUsableVectors_FailsNamingTheField(string json, string expectedFragment)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains(expectedFragment, error);
    }

    [Fact]
    public void TryParse_IgnoresUnknownFields()
    {
        var ok = HarnessCommand.TryParse("""{"command":"quit","id":7}""", out var command, out _);

        Assert.True(ok);
        Assert.Equal(HarnessCommandKind.Quit, command.Kind);
    }

    [Theory]
    [InlineData("""{"command":"load-level"}""", "path")]
    [InlineData("""{"command":"load-level","path":""}""", "path")]
    [InlineData("""{"command":"screenshot","path":"  "}""", "path")]
    [InlineData("""{"command":"load-level","path":3}""", "path")]
    [InlineData("""{"command":"load-bundle"}""", "path")]
    public void TryParse_PathCommandWithoutUsablePath_FailsNamingPath(string json, string expectedFragment)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains(expectedFragment, error);
    }

    [Theory]
    [InlineData("""{"command":"reboot"}""", "reboot")]
    [InlineData("""{"command":"Quit"}""", "Quit")]
    public void TryParse_UnknownCommand_FailsNamingTheCommand(string json, string expectedFragment)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains(expectedFragment, error);
    }

    [Theory]
    [InlineData("")]
    [InlineData("   ")]
    [InlineData("not json")]
    [InlineData("{")]
    [InlineData("[]")]
    [InlineData("null")]
    [InlineData("""{"path":"x"}""")]
    [InlineData("""{"command":5}""")]
    public void TryParse_MalformedInput_FailsWithoutThrowing(string json)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.False(string.IsNullOrEmpty(error));
    }

    [Fact]
    public void TryParse_KeyTap_ReadsKeyAndModifiers()
    {
        var ok = HarnessCommand.TryParse("""{"command":"key","action":"tap","key":"R","modifiers":["LeftShift"]}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.Key, command.Kind);
        Assert.Equal("key", command.Name);
        Assert.Equal("tap", command.Input.Action);
        Assert.Equal("R", command.Input.Key);
        Assert.Equal(new[] { "LeftShift" }, command.Input.Modifiers);
    }

    [Theory]
    [InlineData("tap")]
    [InlineData("down")]
    [InlineData("up")]
    public void TryParse_Key_AcceptsEachAction(string action)
    {
        var ok = HarnessCommand.TryParse($$"""{"command":"key","action":"{{action}}","key":"Escape"}""", out var command, out _);

        Assert.True(ok);
        Assert.Equal(action, command.Input.Action);
        Assert.Empty(command.Input.Modifiers);
    }

    [Theory]
    [InlineData("""{"command":"key","key":"R"}""", "action")]
    [InlineData("""{"command":"key","action":"hold","key":"R"}""", "hold")]
    [InlineData("""{"command":"key","action":"tap"}""", "key")]
    [InlineData("""{"command":"key","action":"tap","key":5}""", "key")]
    [InlineData("""{"command":"key","action":"tap","key":"r"}""", "r")]
    [InlineData("""{"command":"key","action":"tap","key":"NotAKey"}""", "NotAKey")]
    [InlineData("""{"command":"key","action":"down","key":"R","modifiers":["LeftShift"]}""", "modifiers")]
    [InlineData("""{"command":"key","action":"tap","key":"R","modifiers":["Bogus"]}""", "Bogus")]
    [InlineData("""{"command":"key","action":"tap","key":"R","modifiers":"LeftShift"}""", "modifiers")]
    [InlineData("""{"command":"key","action":"tap","key":"R","modifiers":[1]}""", "modifiers")]
    public void TryParse_KeyInvalid_IsRejectedNamingTheProblem(string json, string expectedFragment)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains(expectedFragment, error);
    }

    [Fact]
    public void TryParse_MouseMove_ReadsCoordinates()
    {
        var ok = HarnessCommand.TryParse("""{"command":"mouse","action":"move","x":960,"y":540.5}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.Mouse, command.Kind);
        Assert.Equal("move", command.Input.Action);
        Assert.Equal(960f, command.Input.X);
        Assert.Equal(540.5f, command.Input.Y);
    }

    [Theory]
    [InlineData("click")]
    [InlineData("down")]
    [InlineData("up")]
    public void TryParse_MouseButtonActions_DefaultToTheLeftButtonWithoutAMove(string action)
    {
        var ok = HarnessCommand.TryParse($$"""{"command":"mouse","action":"{{action}}"}""", out var command, out _);

        Assert.True(ok);
        Assert.Equal(0, command.Input.Button);
        Assert.Null(command.Input.X);
        Assert.Null(command.Input.Y);
    }

    [Fact]
    public void TryParse_MouseClick_ReadsButtonAndMoveFirstPosition()
    {
        var ok = HarnessCommand.TryParse("""{"command":"mouse","action":"click","button":1,"x":10,"y":20}""", out var command, out _);

        Assert.True(ok);
        Assert.Equal(1, command.Input.Button);
        Assert.Equal(10f, command.Input.X);
        Assert.Equal(20f, command.Input.Y);
    }

    [Fact]
    public void TryParse_MouseClear_NeedsNoCoordinates()
    {
        var ok = HarnessCommand.TryParse("""{"command":"mouse","action":"clear"}""", out var command, out _);

        Assert.True(ok);
        Assert.Equal("clear", command.Input.Action);
    }

    [Theory]
    [InlineData("""{"command":"mouse"}""", "action")]
    [InlineData("""{"command":"mouse","action":"drag"}""", "drag")]
    [InlineData("""{"command":"mouse","action":"move"}""", "x")]
    [InlineData("""{"command":"mouse","action":"move","x":1}""", "y")]
    [InlineData("""{"command":"mouse","action":"move","x":"1","y":2}""", "x")]
    [InlineData("""{"command":"mouse","action":"click","x":1}""", "y")]
    [InlineData("""{"command":"mouse","action":"click","y":1}""", "x")]
    [InlineData("""{"command":"mouse","action":"click","button":3}""", "button")]
    [InlineData("""{"command":"mouse","action":"click","button":-1}""", "button")]
    [InlineData("""{"command":"mouse","action":"down","button":"left"}""", "button")]
    [InlineData("""{"command":"mouse","action":"up","button":1.5}""", "button")]
    public void TryParse_MouseInvalid_IsRejectedNamingTheProblem(string json, string expectedFragment)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains(expectedFragment, error);
    }

    [Fact]
    public void TryParse_Type_ReadsTextWithControlCharacters()
    {
        var ok = HarnessCommand.TryParse("""{"command":"type","text":"ab\b\n"}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.Type, command.Kind);
        Assert.Equal("ab\b\n", command.Input.Text);
    }

    [Fact]
    public void TryParse_Type_AcceptsExactlyTheMaximumLength()
    {
        var text = new string('a', HarnessCommand.MaxTypeLength);

        Assert.True(HarnessCommand.TryParse($$"""{"command":"type","text":"{{text}}"}""", out _, out _));
    }

    [Theory]
    [InlineData("""{"command":"type"}""")]
    [InlineData("""{"command":"type","text":""}""")]
    [InlineData("""{"command":"type","text":5}""")]
    public void TryParse_TypeWithoutText_IsRejectedNamingText(string json)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains("text", error);
    }

    [Fact]
    public void TryParse_TypeOverTheMaximumLength_IsRejected()
    {
        var text = new string('a', HarnessCommand.MaxTypeLength + 1);

        var ok = HarnessCommand.TryParse($$"""{"command":"type","text":"{{text}}"}""", out _, out var error);

        Assert.False(ok);
        Assert.Contains("200", error);
    }

    [Fact]
    public void TryParse_TeleportPosition_ReturnsTheWorldPoint()
    {
        var ok = HarnessCommand.TryParse("""{"command":"teleport","position":[1.5,0,-200]}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.Teleport, command.Kind);
        Assert.Equal("teleport", command.Name);
        Assert.Equal(new[] { 1.5f, 0f, -200f }, command.Teleport.Position);
        Assert.Null(command.Teleport.Cell);
    }

    [Fact]
    public void TryParse_TeleportCell_ReturnsTheCell()
    {
        var ok = HarnessCommand.TryParse("""{"command":"teleport","cell":[3,12]}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.Teleport, command.Kind);
        Assert.Equal(new[] { 3, 12 }, command.Teleport.Cell);
        Assert.Null(command.Teleport.Position);
    }

    [Theory]
    [InlineData("""{"command":"teleport"}""", "position")]
    [InlineData("""{"command":"teleport","position":[1,2,3],"cell":[1,2]}""", "exactly one")]
    [InlineData("""{"command":"teleport","position":[1,2]}""", "position")]
    [InlineData("""{"command":"teleport","position":[1,2,3,4]}""", "position")]
    [InlineData("""{"command":"teleport","position":[1,"a",3]}""", "position")]
    [InlineData("""{"command":"teleport","cell":[1]}""", "cell")]
    [InlineData("""{"command":"teleport","cell":[1,2,3]}""", "cell")]
    [InlineData("""{"command":"teleport","cell":[1.5,2]}""", "cell")]
    [InlineData("""{"command":"teleport","cell":"1,2"}""", "cell")]
    public void TryParse_TeleportWithoutExactlyOneUsableTarget_FailsNamingTheField(string json, string expectedFragment)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains(expectedFragment, error);
    }

    [Fact]
    public void TryParse_DismissLevelUp_DefaultsToTheFirstOffer()
    {
        var ok = HarnessCommand.TryParse("""{"command":"dismiss-levelup"}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.DismissLevelUp, command.Kind);
        Assert.Equal("dismiss-levelup", command.Name);
        Assert.Equal(0, command.Choice);
    }

    [Fact]
    public void TryParse_DismissLevelUp_CarriesTheChoice()
    {
        var ok = HarnessCommand.TryParse("""{"command":"dismiss-levelup","choice":3}""", out var command, out _);

        Assert.True(ok);
        Assert.Equal(3, command.Choice);
    }

    [Theory]
    [InlineData("""{"command":"dismiss-levelup","choice":-1}""")]
    [InlineData("""{"command":"dismiss-levelup","choice":1.5}""")]
    [InlineData("""{"command":"dismiss-levelup","choice":"first"}""")]
    public void TryParse_DismissLevelUpWithABadChoice_FailsNamingTheField(string json)
    {
        var ok = HarnessCommand.TryParse(json, out _, out var error);

        Assert.False(ok);
        Assert.Contains("choice", error);
    }

    [Fact]
    public void KeyNames_ListsTheDocumentedGroupsAndNoDuplicates()
    {
        string[] expected =
        [
            "A", "Z", "Alpha0", "Alpha9", "Keypad0", "Keypad9", "F1", "F12", "UpArrow", "DownArrow", "LeftArrow", "RightArrow",
            "Escape", "Return", "Backspace", "Delete", "Space", "Tab",
            "LeftShift", "RightShift", "LeftControl", "RightControl", "LeftAlt", "RightAlt",
        ];

        Assert.All(expected, name => Assert.True(KeyNames.IsValid(name), name));
        Assert.Equal(KeyNames.All.Count, KeyNames.All.Distinct().Count());
        Assert.False(KeyNames.IsValid("a"));
        Assert.False(KeyNames.IsValid(null));
    }

    [Fact]
    public void TryParse_ClickWidget_ReadsTheName()
    {
        var ok = HarnessCommand.TryParse("""{"command":"click-widget","name":"Save"}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.ClickWidget, command.Kind);
        Assert.Equal("Save", command.Input.Text);
    }

    [Theory]
    [InlineData("""{"command":"click-widget"}""")]
    [InlineData("""{"command":"click-widget","name":""}""")]
    public void TryParse_ClickWidget_RejectsAMissingName(string json)
    {
        Assert.False(HarnessCommand.TryParse(json, out _, out var error));
        Assert.Contains("'name'", error);
    }

    [Fact]
    public void TryParse_SaveLevel_LevelIsOptional()
    {
        Assert.True(HarnessCommand.TryParse("""{"command":"save-level"}""", out var bare, out _));
        Assert.Equal(HarnessCommandKind.SaveLevel, bare.Kind);
        Assert.Null(bare.Path);

        Assert.True(HarnessCommand.TryParse("""{"command":"save-level","level":"my level"}""", out var named, out var error));
        Assert.Null(error);
        Assert.Equal("my level", named.Path);
    }

    [Theory]
    [InlineData("""{"command":"save-level","level":""}""")]
    [InlineData("""{"command":"save-level","level":5}""")]
    public void TryParse_SaveLevel_RejectsABadLevel(string json)
    {
        Assert.False(HarnessCommand.TryParse(json, out _, out var error));
        Assert.Contains("'level'", error);
    }

    [Fact]
    public void TryParse_ListLevels_NeedsNoArguments()
    {
        Assert.True(HarnessCommand.TryParse("""{"command":"list-levels"}""", out var command, out _));
        Assert.Equal(HarnessCommandKind.ListLevels, command.Kind);
    }

    [Fact]
    public void TryParse_UiTree_NeedsNoArguments()
    {
        var ok = HarnessCommand.TryParse("""{"command":"ui-tree"}""", out var command, out _);

        Assert.True(ok);
        Assert.Equal(HarnessCommandKind.UiTree, command.Kind);
        Assert.Null(command.Input.X);
        Assert.Null(command.Input.Y);
    }

    [Fact]
    public void TryParse_UiTree_ReadsAPoint()
    {
        var ok = HarnessCommand.TryParse("""{"command":"ui-tree","x":120,"y":35.5}""", out var command, out _);

        Assert.True(ok);
        Assert.Equal(120f, command.Input.X);
        Assert.Equal(35.5f, command.Input.Y);
    }

    [Theory]
    [InlineData("""{"command":"ui-tree","x":1}""")]
    [InlineData("""{"command":"ui-tree","y":1}""")]
    public void TryParse_UiTree_RejectsAHalfPoint(string json)
    {
        Assert.False(HarnessCommand.TryParse(json, out _, out var error));
        Assert.Contains("missing number field", error);
    }

    [Fact]
    public void TryParse_QueryObjects_ReadsTypeAndFields()
    {
        var ok = HarnessCommand.TryParse("""{"command":"query-objects","type":"MapData","fields":["eMap","icon"]}""", out var command, out var error);

        Assert.True(ok);
        Assert.Null(error);
        Assert.Equal(HarnessCommandKind.QueryObjects, command.Kind);
        Assert.Equal("query-objects", command.Name);
        Assert.Equal("MapData", command.Query.TypeName);
        Assert.Equal(new[] { "eMap", "icon" }, command.Query.Fields);
    }

    [Fact]
    public void TryParse_QueryObjects_FieldsDefaultToNone()
    {
        var ok = HarnessCommand.TryParse("""{"command":"query-objects","type":"MapData"}""", out var command, out _);

        Assert.True(ok);
        Assert.Empty(command.Query.Fields);
    }

    [Theory]
    [InlineData("""{"command":"query-objects"}""", "type")]
    [InlineData("""{"command":"query-objects","type":""}""", "type")]
    [InlineData("""{"command":"query-objects","type":5}""", "type")]
    [InlineData("""{"command":"query-objects","type":"MapData","fields":"eMap"}""", "fields")]
    [InlineData("""{"command":"query-objects","type":"MapData","fields":[1]}""", "fields")]
    [InlineData("""{"command":"query-objects","type":"MapData","fields":[""]}""", "fields")]
    public void TryParse_QueryObjectsWithUnusableArguments_FailsNamingTheField(string json, string expectedFragment)
    {
        Assert.False(HarnessCommand.TryParse(json, out _, out var error));
        Assert.Contains(expectedFragment, error);
    }
}
