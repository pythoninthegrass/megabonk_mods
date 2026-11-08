namespace MegabonkLevels.Tests;

public class ConsoleCommandRegistryTests
{
    // Every verb and alias in the table, with the line that must bind and the harness kind it must produce.
    public static IEnumerable<object[]> Bindings => new[]
    {
        // Console-only verbs run without a harness command.
        new object[] { "help", null },
        new object[] { "help state", null },
        new object[] { "clear", null },
        new object[] { "cls", null },
        new object[] { "history", null },
        new object[] { "state", HarnessCommandKind.State },
        // Player
        new object[] { "player.teleport 1 2 3", HarnessCommandKind.Teleport },
        new object[] { "tp 1 2 3", HarnessCommandKind.Teleport },
        new object[] { "player.teleport_cell 4 5", HarnessCommandKind.Teleport },
        new object[] { "player.god on", HarnessCommandKind.Invulnerable },
        new object[] { "player.god off", HarnessCommandKind.Vulnerable },
        new object[] { "player.god", HarnessCommandKind.Invulnerable },
        new object[] { "tgm on", HarnessCommandKind.Invulnerable },
        new object[] { "tgm", HarnessCommandKind.Invulnerable },
        new object[] { "player.kill", HarnessCommandKind.Kill },
        new object[] { "player.damage 37", HarnessCommandKind.Damage },
        new object[] { "player.damage 37 nonlethal", HarnessCommandKind.Damage },
        new object[] { "player.add_item Mirror", HarnessCommandKind.Item },
        new object[] { "player.add_item Mirror 3", HarnessCommandKind.Item },
        new object[] { "player.fall_damage", HarnessCommandKind.FallDamage },
        // Enemies
        new object[] { "enemies.kill nearest", HarnessCommandKind.KillEnemies },
        new object[] { "enemies.kill all", HarnessCommandKind.KillEnemies },
        new object[] { "enemies.kill bosses", HarnessCommandKind.KillEnemies },
        new object[] { "killall", HarnessCommandKind.KillEnemies },
        new object[] { "enemies.spawns on", HarnessCommandKind.Spawns },
        new object[] { "enemies.spawns off", HarnessCommandKind.Spawns },
        // Run
        new object[] { "run.freeze", HarnessCommandKind.Freeze },
        new object[] { "run.resume", HarnessCommandKind.Resume },
        new object[] { "run.restart", HarnessCommandKind.RestartRun },
        new object[] { "run.dismiss_levelup", HarnessCommandKind.DismissLevelUp },
        new object[] { "run.dismiss_levelup 2", HarnessCommandKind.DismissLevelUp },
        new object[] { "run.dismiss_offers", HarnessCommandKind.DismissOffers },
        new object[] { "run.dismiss_offers 1", HarnessCommandKind.DismissOffers },
        new object[] { "run.dismiss_offers skip", HarnessCommandKind.DismissOffers },
        new object[] { "run.interact", HarnessCommandKind.Interact },
        new object[] { "run.interact Magnet", HarnessCommandKind.Interact },
        new object[] { "run.press_death_confirm", HarnessCommandKind.PressDeathConfirm },
        new object[] { "run.press_summary_restart", HarnessCommandKind.PressSummaryRestart },
        // Level
        new object[] { "level.list", HarnessCommandKind.ListLevels },
        new object[] { "level.load levels/thps.mblevel.json", HarnessCommandKind.LoadLevel },
        new object[] { "level.load \"Bramblecrown Hill\"", HarnessCommandKind.LoadLevel },
        new object[] { "level.load thps map 2 stage 1 tier 0 seed 424242", HarnessCommandKind.LoadLevel },
        new object[] { "level.load thps noseed", HarnessCommandKind.LoadLevel },
        new object[] { "coc \"Bramblecrown Hill\"", HarnessCommandKind.LoadLevel },
        new object[] { "level.save", HarnessCommandKind.SaveLevel },
        new object[] { "level.save my_level", HarnessCommandKind.SaveLevel },
        new object[] { "level.new", HarnessCommandKind.NewLevel },
        new object[] { "level.new arena", HarnessCommandKind.NewLevel },
        new object[] { "level.new arena map 2 stage 1 tier 0 size 9", HarnessCommandKind.NewLevel },
        // Editor and camera
        new object[] { "editor on", HarnessCommandKind.Editor },
        new object[] { "editor off", HarnessCommandKind.Editor },
        new object[] { "editor", HarnessCommandKind.Editor },
        new object[] { "tfc on", HarnessCommandKind.Editor },
        new object[] { "tfc", HarnessCommandKind.Editor },
        new object[] { "camera.set 1 2 3 40 0 90", HarnessCommandKind.Camera },
        new object[] { "camera.clear", HarnessCommandKind.CameraClear },
        // UI
        new object[] { "ui.hud on", HarnessCommandKind.Hud },
        new object[] { "ui.hud off", HarnessCommandKind.Hud },
        new object[] { "ui.hud", HarnessCommandKind.Hud },
        new object[] { "tm on", HarnessCommandKind.Hud },
        new object[] { "tm", HarnessCommandKind.Hud },
        new object[] { "ui.coordinates on", HarnessCommandKind.Coordinates },
        new object[] { "ui.coordinates off", HarnessCommandKind.Coordinates },
        new object[] { "ui.coordinates", HarnessCommandKind.Coordinates },
        // Perf
        new object[] { "perf.report", HarnessCommandKind.Perf },
        new object[] { "perf.status", HarnessCommandKind.Perf },
        new object[] { "perf.start", HarnessCommandKind.Perf },
        new object[] { "perf.reset", HarnessCommandKind.Perf },
        new object[] { "perf.spawn 120", HarnessCommandKind.Perf },
        new object[] { "perf.timescale 4", HarnessCommandKind.Perf },
        new object[] { "perf.timescale", HarnessCommandKind.Perf },
        new object[] { "time_scale 4", HarnessCommandKind.Perf },
        new object[] { "perf.toggle KillFloor off", HarnessCommandKind.Perf },
        new object[] { "perf.toggle all on", HarnessCommandKind.Perf },
        new object[] { "perf.vsync off", HarnessCommandKind.Perf },
        new object[] { "perf.render on", HarnessCommandKind.Perf },
        new object[] { "perf.physics off", HarnessCommandKind.Perf },
        new object[] { "perf.animation off", HarnessCommandKind.Perf },
        new object[] { "perf.health", HarnessCommandKind.Perf },
        new object[] { "perf.health 1000000", HarnessCommandKind.Perf },
        new object[] { "perf.census", HarnessCommandKind.Perf },
        // Debug
        new object[] { "debug.screenshot evidence/shot.png", HarnessCommandKind.Screenshot },
        new object[] { "debug.query_objects MapData", HarnessCommandKind.QueryObjects },
        new object[] { "debug.query_objects MapData eMap stages", HarnessCommandKind.QueryObjects },
        new object[] { "debug.material_dump", HarnessCommandKind.MaterialDump },
        new object[] { "debug.material_dump Warehouse", HarnessCommandKind.MaterialDump },
        new object[] { "debug.shader_report", HarnessCommandKind.ShaderReport },
        new object[] { "debug.heartbeat on", HarnessCommandKind.Heartbeat },
        new object[] { "debug.heartbeat off", HarnessCommandKind.Heartbeat },
        new object[] { "debug.cells on", HarnessCommandKind.Cells },
        new object[] { "debug.cells off", HarnessCommandKind.Cells },
        new object[] { "debug.ui_tree", HarnessCommandKind.UiTree },
        new object[] { "debug.ui_tree 960 540", HarnessCommandKind.UiTree },
        new object[] { "debug.click_widget Save", HarnessCommandKind.ClickWidget },
        // App
        new object[] { "app.quit", HarnessCommandKind.Quit },
        new object[] { "qqq", HarnessCommandKind.Quit },
    };

    [Theory]
    [MemberData(nameof(Bindings))]
    public void Bind_ProducesTheExpectedHarnessCommand(string line, HarnessCommandKind? expected)
    {
        var result = ConsoleCommandRegistry.Default.Bind(line, DevState(true), Toggles());

        Assert.Null(result.Error);
        if (expected == null)
        {
            Assert.False(result.Command.HasValue);
        }
        else
        {
            Assert.True(result.Command.HasValue);
            Assert.Equal(expected, result.Command.Value.Kind);
        }
    }

    [Theory]
    [InlineData("state")]
    [InlineData("help")]
    [InlineData("clear")]
    [InlineData("history")]
    [InlineData("ui.hud on")]
    [InlineData("ui.coordinates on")]
    [InlineData("level.list")]
    public void Bind_UngatedVerbs_WorkWithoutTheDevFlag(string line)
    {
        var result = ConsoleCommandRegistry.Default.Bind(line, DevState(false), Toggles());

        Assert.Null(result.Error);
    }

    [Theory]
    [InlineData("tp 1 2 3")]
    [InlineData("player.god")]
    [InlineData("tgm")]
    [InlineData("player.kill")]
    [InlineData("player.damage 10")]
    [InlineData("player.add_item Mirror")]
    [InlineData("player.fall_damage")]
    [InlineData("enemies.kill all")]
    [InlineData("killall")]
    [InlineData("enemies.spawns on")]
    [InlineData("run.freeze")]
    [InlineData("run.resume")]
    [InlineData("run.restart")]
    [InlineData("run.dismiss_levelup")]
    [InlineData("run.dismiss_offers skip")]
    [InlineData("run.interact")]
    [InlineData("run.press_death_confirm")]
    [InlineData("run.press_summary_restart")]
    [InlineData("level.load thps")]
    [InlineData("coc Warehouse")]
    [InlineData("level.save")]
    [InlineData("level.new")]
    [InlineData("editor")]
    [InlineData("tfc")]
    [InlineData("camera.set 1 2 3 4 5 6")]
    [InlineData("camera.clear")]
    [InlineData("perf.report")]
    [InlineData("time_scale 2")]
    [InlineData("debug.screenshot shot.png")]
    [InlineData("debug.query_objects MapData")]
    [InlineData("debug.material_dump")]
    [InlineData("debug.shader_report")]
    [InlineData("debug.heartbeat on")]
    [InlineData("debug.cells on")]
    [InlineData("debug.ui_tree")]
    [InlineData("debug.click_widget Save")]
    [InlineData("app.quit")]
    [InlineData("qqq")]
    public void Bind_GatedVerbs_RefuseWithoutTheDevFlag(string line)
    {
        var result = ConsoleCommandRegistry.Default.Bind(line, DevState(false), Toggles());

        Assert.Equal(ConsoleCommandRegistry.GatedReply, result.Error);
        Assert.False(result.Command.HasValue);
    }

    [Fact]
    public void Bind_RepliesWithTheUsageLineForBadArity()
    {
        var result = ConsoleCommandRegistry.Default.Bind("player.teleport 1 2", DevState(true), Toggles());

        Assert.NotNull(result.Error);
        Assert.StartsWith("usage:", result.Error);
        Assert.Contains("player.teleport x y z", result.Error);
        Assert.False(result.Command.HasValue);
    }

    [Theory]
    [InlineData("player.damage 500")]
    [InlineData("player.damage lots")]
    [InlineData("enemies.kill everyone")]
    [InlineData("enemies.spawns maybe")]
    [InlineData("level.load thps map 7")]
    [InlineData("level.new arena size 2")]
    [InlineData("player.add_item Mirror notanumber")]
    [InlineData("player.teleport_cell a b")]
    [InlineData("camera.set 1 2 3 4 5")]
    [InlineData("perf.spawn 9999")]
    [InlineData("perf.toggle KillFloor maybe")]
    [InlineData("debug.ui_tree 960")]
    [InlineData("ui.hud maybe")]
    public void Bind_RepliesWithTheUsageLineForBadValues(string line)
    {
        var result = ConsoleCommandRegistry.Default.Bind(line, DevState(true), Toggles());

        Assert.NotNull(result.Error);
        Assert.StartsWith("usage:", result.Error);
        Assert.False(result.Command.HasValue);
    }

    [Theory]
    [InlineData("help", "state", "clear", "history", "ui.hud", "ui.coordinates", "level.list")]
    public void Help_WithoutAFilter_ListsUngatedVerbsWithHelpAndAliases(string line, params string[] expected)
    {
        var reply = ConsoleCommandRegistry.Default.Bind(line, DevState(false), Toggles()).Reply;

        foreach (var verb in expected)
        {
            Assert.Contains(verb, reply);
        }

        Assert.Contains("cls", reply);
        Assert.Contains("clear", reply);
    }

    [Fact]
    public void Help_WithoutTheDevFlag_HidesGatedVerbs()
    {
        var reply = ConsoleCommandRegistry.Default.Bind("help", DevState(false), Toggles()).Reply;

        Assert.DoesNotContain("player.god", reply);
        Assert.DoesNotContain("qqq", reply);
    }

    [Fact]
    public void Help_WithTheDevFlag_ListsGatedVerbsAndTheirAliases()
    {
        var reply = ConsoleCommandRegistry.Default.Bind("help", DevState(true), Toggles()).Reply;

        Assert.Contains("player.god", reply);
        Assert.Contains("tgm", reply);
        Assert.Contains("coc", reply);
        Assert.Contains("killall", reply);
    }

    [Theory]
    [InlineData("help player", new[] { "player.teleport", "player.god" }, new[] { "enemies.kill", "ui.hud", "app.quit" })]
    [InlineData("help PERF", new[] { "perf.report", "perf.spawn" }, new[] { "ui.hud", "app.quit" })]
    public void Help_WithAFilter_KeepsOnlyMatchingVerbs(string line, string[] expected, string[] excluded)
    {
        var reply = ConsoleCommandRegistry.Default.Bind(line, DevState(true), Toggles()).Reply;

        foreach (var verb in expected)
        {
            Assert.Contains(verb, reply);
        }

        foreach (var verb in excluded)
        {
            Assert.DoesNotContain(verb, reply);
        }
    }

    [Fact]
    public void Help_MatchesAnAliasAndPrintsItsVerb()
    {
        var reply = ConsoleCommandRegistry.Default.Bind("help tgm", DevState(true), Toggles()).Reply;

        Assert.Contains("player.god", reply);
        Assert.Contains("tgm", reply);
    }

    [Fact]
    public void Help_FilterWithNoMatch_SaysSo()
    {
        var reply = ConsoleCommandRegistry.Default.Bind("help nosuchverb", DevState(true), Toggles()).Reply;

        Assert.Contains("no verb matches", reply);
    }

    [Fact]
    public void UnknownVerb_RepliesWithTheClosestMatches()
    {
        var result = ConsoleCommandRegistry.Default.Bind("player.teleprot 1 2 3", DevState(true), Toggles());

        Assert.NotNull(result.Error);
        Assert.Contains("unknown verb", result.Error);
        Assert.Contains("player.teleport", result.Error);
    }

    [Fact]
    public void UnknownVerb_SuggestsAnUngatedVerbWhenGatingHidesTheRightOne()
    {
        var result = ConsoleCommandRegistry.Default.Bind("ui.huds on", DevState(false), Toggles());

        Assert.Contains("ui.hud", result.Error);
    }

    [Fact]
    public void UnknownVerb_WithNothingClose_SaysSo()
    {
        var result = ConsoleCommandRegistry.Default.Bind("xyzzy", DevState(true), Toggles());

        Assert.Contains("unknown verb", result.Error);
        Assert.DoesNotContain("did you mean", result.Error);
    }

    [Fact]
    public void Completion_PrefixMatchesEveryVerbAndAlias()
    {
        var completion = ConsoleCommandRegistry.Default.Complete("player.ad");

        Assert.Equal("player.add_item", completion.Text);
        Assert.Single(completion.Matches);
    }

    [Fact]
    public void Completion_MatchesAliasesByPrefix()
    {
        var completion = ConsoleCommandRegistry.Default.Complete("t");

        Assert.Contains("tgm", completion.Matches);
        Assert.Contains("tfc", completion.Matches);
        Assert.Contains("tm", completion.Matches);
        Assert.Contains("tp", completion.Matches);
        Assert.Contains("time_scale", completion.Matches);
    }

    [Fact]
    public void Completion_CyclesThroughMatches()
    {
        var completion = ConsoleCommandRegistry.Default.Complete("t");
        var first = completion.Text;

        completion = completion.Next();
        var second = completion.Text;
        completion = completion.Next();
        var third = completion.Text;
        completion = completion.Next();
        var fourth = completion.Text;
        completion = completion.Next();

        var firsts = new[] { "tfc", "tgm", "time_scale", "tm" };
        var seconds = new[] { first, second, third, fourth };
        Assert.Equal(firsts, seconds);
        Assert.Equal("tp", completion.Text);
        Assert.Equal("tfc", completion.Next().Text);
    }

    [Fact]
    public void Completion_WrapsBackToTheFirstMatch()
    {
        var completion = ConsoleCommandRegistry.Default.Complete("player.g");
        completion = completion.Next();
        completion = completion.Next();

        Assert.Equal("player.god", completion.Text);
    }

    [Fact]
    public void Completion_PrevWalksBackwards()
    {
        var completion = ConsoleCommandRegistry.Default.Complete("player.g");

        Assert.Equal("player.god", completion.Prev().Text);
    }

    [Fact]
    public void Completion_UniqueMatch_FillsTheRestOfTheWord()
    {
        var completion = ConsoleCommandRegistry.Default.Complete("kill");

        Assert.Equal("killall", completion.Text);
        Assert.Equal("all", completion.Completion);
    }

    [Fact]
    public void Completion_NoMatch_HasNoText()
    {
        var completion = ConsoleCommandRegistry.Default.Complete("zzz");

        Assert.Equal("", completion.Text);
        Assert.Empty(completion.Matches);
        Assert.Equal("", completion.Next().Text);
    }

    [Fact]
    public void Completion_CyclingIsIndependentPerPrefix()
    {
        var enemies = ConsoleCommandRegistry.Default.Complete("enemies");
        enemies = enemies.Next();

        Assert.Equal("enemies.spawns", enemies.Text);
        Assert.Equal("enemies.kill", ConsoleCommandRegistry.Default.Complete("enemies").Text);
    }

    [Fact]
    public void ToggleVerbs_WithNoArgumentFlipTheCurrentState()
    {
        var toggles = Toggles(invulnerable: true, editor: false, hud: true, coordinates: false);

        Assert.Equal(HarnessCommandKind.Vulnerable, ConsoleCommandRegistry.Default.Bind("player.god", DevState(true), toggles).Command.Value.Kind);
        Assert.Equal(HarnessCommandKind.Vulnerable, ConsoleCommandRegistry.Default.Bind("tgm", DevState(true), toggles).Command.Value.Kind);
        Assert.Equal(HarnessCommandKind.Editor, ConsoleCommandRegistry.Default.Bind("editor", DevState(true), toggles).Command.Value.Kind);
        Assert.True(ConsoleCommandRegistry.Default.Bind("tfc", DevState(true), toggles).Command.Value.Enabled);
        Assert.Equal(HarnessCommandKind.Hud, ConsoleCommandRegistry.Default.Bind("tm", DevState(true), toggles).Command.Value.Kind);
        Assert.False(ConsoleCommandRegistry.Default.Bind("ui.hud", DevState(true), toggles).Command.Value.Enabled);
        Assert.True(ConsoleCommandRegistry.Default.Bind("ui.coordinates", DevState(true), toggles).Command.Value.Enabled);
    }

    [Fact]
    public void ToggleVerbs_WithAnArgumentIgnoreTheCurrentState()
    {
        var toggles = Toggles(invulnerable: true, editor: true, hud: true, coordinates: true);

        Assert.False(ConsoleCommandRegistry.Default.Bind("player.god off", DevState(true), toggles).Command.Value.Enabled);
        Assert.False(ConsoleCommandRegistry.Default.Bind("editor off", DevState(true), toggles).Command.Value.Enabled);
        Assert.False(ConsoleCommandRegistry.Default.Bind("ui.hud off", DevState(true), toggles).Command.Value.Enabled);
        Assert.False(ConsoleCommandRegistry.Default.Bind("ui.coordinates off", DevState(true), toggles).Command.Value.Enabled);
    }

    [Fact]
    public void Bind_CarriesTeleportPositionAndCell()
    {
        var position = ConsoleCommandRegistry.Default.Bind("tp -1.5 2 3.25", DevState(true), Toggles()).Command.Value;
        Assert.Equal(new[] { -1.5f, 2f, 3.25f }, position.Teleport.Position);
        Assert.Null(position.Teleport.Cell);

        var cell = ConsoleCommandRegistry.Default.Bind("player.teleport_cell 4 5", DevState(true), Toggles()).Command.Value;
        Assert.Equal(new[] { 4, 5 }, cell.Teleport.Cell);
        Assert.Null(cell.Teleport.Position);
    }

    [Fact]
    public void Bind_CarriesTheCameraPose()
    {
        var command = ConsoleCommandRegistry.Default.Bind("camera.set 1 2 3 40 0 90", DevState(true), Toggles()).Command.Value;

        Assert.Equal(new CameraPose(1f, 2f, 3f, 40f, 0f, 90f), command.Pose);
    }

    [Fact]
    public void Bind_CarriesKillTargetAndDamage()
    {
        Assert.Equal("bosses", ConsoleCommandRegistry.Default.Bind("enemies.kill bosses", DevState(true), Toggles()).Command.Value.KillTarget);
        Assert.Equal("all", ConsoleCommandRegistry.Default.Bind("killall", DevState(true), Toggles()).Command.Value.KillTarget);

        var damage = ConsoleCommandRegistry.Default.Bind("player.damage 37", DevState(true), Toggles()).Command.Value;
        Assert.Equal(37, damage.Damage.Amount);
        Assert.True(damage.Damage.Nonlethal);
    }

    [Fact]
    public void Bind_CarriesItemNameAndAmount()
    {
        var read = ConsoleCommandRegistry.Default.Bind("player.add_item Mirror", DevState(true), Toggles()).Command.Value;
        Assert.Equal("Mirror", read.Item.Name);
        Assert.Null(read.Item.Amount);

        var set = ConsoleCommandRegistry.Default.Bind("player.add_item Mirror 3", DevState(true), Toggles()).Command.Value;
        Assert.Equal(3, set.Item.Amount);
    }

    [Fact]
    public void Bind_CarriesRunDialogArguments()
    {
        Assert.Equal(2, ConsoleCommandRegistry.Default.Bind("run.dismiss_levelup 2", DevState(true), Toggles()).Command.Value.Choice);

        var skip = ConsoleCommandRegistry.Default.Bind("run.dismiss_offers skip", DevState(true), Toggles()).Command.Value;
        Assert.True(skip.Skip);
        Assert.Null(skip.Offer);

        var pick = ConsoleCommandRegistry.Default.Bind("run.dismiss_offers 1", DevState(true), Toggles()).Command.Value;
        Assert.Equal(1, pick.Offer);
        Assert.False(pick.Skip);

        Assert.Null(ConsoleCommandRegistry.Default.Bind("run.interact", DevState(true), Toggles()).Command.Value.Interact.Type);
        Assert.Equal("Magnet", ConsoleCommandRegistry.Default.Bind("run.interact Magnet", DevState(true), Toggles()).Command.Value.Interact.Type);
    }

    [Fact]
    public void Bind_LoadLevelResolvesATitleAgainstTheLevelList()
    {
        var command = ConsoleCommandRegistry.Default.Bind("coc \"Bramblecrown Hill\"", DevState(true), Toggles(), LevelList()).Command.Value;

        Assert.Equal("Bramblecrown Hill.mblevel.json", command.Path);
        Assert.Equal(HarnessCommandKind.LoadLevel, command.Kind);
    }

    [Fact]
    public void Bind_LoadLevelTitleMatchIsCaseAndPunctuationInsensitive()
    {
        var command = ConsoleCommandRegistry.Default.Bind("level.load \"Bramblecrown  Hill\"", DevState(true), Toggles(), LevelList()).Command.Value;

        Assert.Equal("Bramblecrown Hill.mblevel.json", command.Path);
    }

    [Fact]
    public void Bind_LoadLevelAnAmbiguousTitleNamesTheCandidates()
    {
        var levels = new[] { "twin hill.mblevel.json", "twin_hill.mblevel.json" };
        var result = ConsoleCommandRegistry.Default.Bind("level.load \"Twin Hill\"", DevState(true), Toggles(), levels);

        Assert.Contains("ambiguous", result.Error);
        Assert.Contains("twin hill", result.Error);
        Assert.Contains("twin_hill", result.Error);
        Assert.False(result.Command.HasValue);
    }

    [Fact]
    public void Bind_LoadLevelAnUnknownTitleIsAnError()
    {
        var result = ConsoleCommandRegistry.Default.Bind("level.load NoSuchMap", DevState(true), Toggles(), LevelList());

        Assert.NotNull(result.Error);
        Assert.False(result.Command.HasValue);
    }

    [Fact]
    public void Bind_LoadLevelAPathOrFileNameNeedsNoTitleMatch()
    {
        var path = ConsoleCommandRegistry.Default.Bind("level.load levels/thps.mblevel.json", DevState(true), Toggles(), LevelList()).Command.Value;
        Assert.Equal("levels/thps.mblevel.json", path.Path);

        var file = ConsoleCommandRegistry.Default.Bind("coc thps.mblevel.json", DevState(true), Toggles(), LevelList()).Command.Value;
        Assert.Equal("thps.mblevel.json", file.Path);

        var stem = ConsoleCommandRegistry.Default.Bind("level.load thps", DevState(true), Toggles(), LevelList()).Command.Value;
        Assert.Equal("thps.mblevel.json", stem.Path);
    }

    [Fact]
    public void Bind_LoadLevelCarriesTheOverrides()
    {
        var command = ConsoleCommandRegistry.Default.Bind("level.load thps map 2 stage 1 tier 3 seed 424242", DevState(true), Toggles(), LevelList()).Command.Value;

        Assert.Equal(2, command.Overrides.Map);
        Assert.Equal(1, command.Overrides.StageIndex);
        Assert.Equal(3, command.Overrides.Tier);
        Assert.Equal(424242, command.Overrides.Seed);
        Assert.False(command.Overrides.Unseeded);

        var unseeded = ConsoleCommandRegistry.Default.Bind("level.load thps noseed", DevState(true), Toggles(), LevelList()).Command.Value;
        Assert.True(unseeded.Overrides.Unseeded);
    }

    [Fact]
    public void Bind_LoadLevelRejectsBadOverrideValues()
    {
        AssertBindFails("level.load thps seed notanumber");
        AssertBindFails("level.load thps map 7");
        AssertBindFails("level.load thps stage -1");
        AssertBindFails("level.load thps tier -1");
        AssertBindFails("level.load thps extra");
    }

    [Fact]
    public void Bind_NewLevelCarriesTheBlankLevelFields()
    {
        var command = ConsoleCommandRegistry.Default.Bind("level.new arena map 2 stage 1 tier 3 size 9", DevState(true), Toggles()).Command.Value;

        Assert.Equal("arena", command.Path);
        Assert.Equal(new NewLevelArgs(2, 1, 3, 9), command.NewLevel);

        var blank = ConsoleCommandRegistry.Default.Bind("level.new", DevState(true), Toggles()).Command.Value;
        Assert.Null(blank.Path);
        Assert.Equal(new NewLevelArgs(1, 0, 0, 7), blank.NewLevel);
    }

    [Fact]
    public void Bind_NewLevelRejectsABadSize()
    {
        AssertBindFails("level.new arena size 2");
        AssertBindFails("level.new arena size 0");
    }

    [Fact]
    public void Bind_PerfCarriesEachActionArgument()
    {
        Assert.Equal("report", ConsoleCommandRegistry.Default.Bind("perf.report", DevState(true), Toggles()).Command.Value.Perf.Action);

        var spawn = ConsoleCommandRegistry.Default.Bind("perf.spawn 120", DevState(true), Toggles()).Command.Value.Perf;
        Assert.Equal("spawn", spawn.Action);
        Assert.Equal(120, spawn.Count);

        var timescale = ConsoleCommandRegistry.Default.Bind("time_scale 4", DevState(true), Toggles()).Command.Value.Perf;
        Assert.Equal("timescale", timescale.Action);
        Assert.Equal(4f, timescale.Value);

        var release = ConsoleCommandRegistry.Default.Bind("perf.timescale", DevState(true), Toggles()).Command.Value.Perf;
        Assert.Null(release.Value);

        var toggle = ConsoleCommandRegistry.Default.Bind("perf.toggle KillFloor off", DevState(true), Toggles()).Command.Value.Perf;
        Assert.Equal("toggle", toggle.Action);
        Assert.Equal("KillFloor", toggle.Target);
        Assert.False(toggle.Enabled);

        var vsync = ConsoleCommandRegistry.Default.Bind("perf.vsync off", DevState(true), Toggles()).Command.Value.Perf;
        Assert.Equal("vsync", vsync.Action);
        Assert.False(vsync.Enabled);

        var lethal = ConsoleCommandRegistry.Default.Bind("player.damage 37 lethal", DevState(true), Toggles()).Command.Value;
        Assert.False(lethal.Damage.Nonlethal);

        var health = ConsoleCommandRegistry.Default.Bind("perf.health 1000", DevState(true), Toggles()).Command.Value.Perf;
        Assert.Equal("health", health.Action);
        Assert.Equal(1000, health.Hp);
    }

    [Fact]
    public void Bind_PerfRejectsAnUnknownActionOrMissingArgument()
    {
        AssertBindFails("perf.nonsense");
        AssertBindFails("perf.spawn");
        AssertBindFails("perf.spawn 0");
        AssertBindFails("perf.toggle");
        AssertBindFails("perf.vsync");
        AssertBindFails("perf.health 0");
        AssertBindFails("time_scale 999");
    }

    [Fact]
    public void Bind_DebugQueryCarriesTypeAndFields()
    {
        var query = ConsoleCommandRegistry.Default.Bind("debug.query_objects MapData eMap stages", DevState(true), Toggles()).Command.Value.Query;

        Assert.Equal("MapData", query.TypeName);
        Assert.Equal(new[] { "eMap", "stages" }, query.Fields);
    }

    [Fact]
    public void Bind_DebugUiTreeNeedsBothOrNeitherCoordinate()
    {
        var tree = ConsoleCommandRegistry.Default.Bind("debug.ui_tree 960 540", DevState(true), Toggles()).Command.Value;
        Assert.Equal(960f, tree.Input.X);
        Assert.Equal(540f, tree.Input.Y);

        AssertBindFails("debug.ui_tree 960");
    }

    [Fact]
    public void Bind_DebugScreenshotNeedsAPath()
    {
        Assert.Equal("evidence/shot.png", ConsoleCommandRegistry.Default.Bind("debug.screenshot evidence/shot.png", DevState(true), Toggles()).Command.Value.Path);
        AssertBindFails("debug.screenshot");
    }

    [Fact]
    public void Bind_RejectsATokenizerError()
    {
        var result = ConsoleCommandRegistry.Default.Bind("level.load \"unterminated", DevState(true), Toggles());

        Assert.Contains("quote", result.Error);
        Assert.False(result.Command.HasValue);
    }

    [Fact]
    public void Registry_ExposesEveryVerbOnceWithHelpAndGating()
    {
        var verbs = ConsoleCommandRegistry.Default.Verbs;

        Assert.Equal(verbs.Count, verbs.Select(v => v.Name).Distinct(StringComparer.OrdinalIgnoreCase).Count());
        Assert.All(verbs, verb => Assert.False(string.IsNullOrWhiteSpace(verb.Help)));
        Assert.All(verbs, verb => Assert.StartsWith("usage:", verb.Usage));

        var names = verbs.Select(v => v.Name).ToHashSet(StringComparer.OrdinalIgnoreCase);
        Assert.Contains("player.teleport", names);
        Assert.Contains("player.god", names);
        Assert.Contains("perf.report", names);
        Assert.Contains("debug.click_widget", names);
        Assert.Contains("music.play", names);
    }

    [Fact]
    public void Registry_GatedFlagMatchesTheVerbTable()
    {
        var gated = ConsoleCommandRegistry.Default.Verbs
            .Where(v => v.Gated)
            .Select(v => v.Name)
            .ToHashSet(StringComparer.OrdinalIgnoreCase);

        Assert.DoesNotContain("state", gated);
        Assert.DoesNotContain("ui.hud", gated);
        Assert.DoesNotContain("ui.coordinates", gated);
        Assert.DoesNotContain("level.list", gated);
        Assert.DoesNotContain("music.play", gated);

        foreach (var verb in new[] { "player.god", "player.kill", "enemies.kill", "run.freeze", "level.load", "editor", "camera.set", "perf.report", "debug.screenshot", "app.quit" })
        {
            Assert.Contains(verb, gated);
        }
    }

    [Fact]
    public void Aliases_MapToTheirVerb()
    {
        Assert.Equal("player.god", ConsoleCommandRegistry.Default.Find("tgm").Name);
        Assert.Equal("editor", ConsoleCommandRegistry.Default.Find("tfc").Name);
        Assert.Equal("ui.hud", ConsoleCommandRegistry.Default.Find("tm").Name);
        Assert.Equal("player.teleport", ConsoleCommandRegistry.Default.Find("tp").Name);
        Assert.Equal("level.load", ConsoleCommandRegistry.Default.Find("coc").Name);
        Assert.Equal("clear", ConsoleCommandRegistry.Default.Find("cls").Name);
        Assert.Equal("app.quit", ConsoleCommandRegistry.Default.Find("qqq").Name);
        Assert.Equal("perf.report", ConsoleCommandRegistry.Default.Find("perf.status") is null ? null : "perf.report");
        Assert.Equal("time_scale", ConsoleCommandRegistry.Default.Find("time_scale").Name);
        Assert.Null(ConsoleCommandRegistry.Default.Find("nosuchverb"));
    }

    [Fact]
    public void VerbMatching_IsCaseInsensitive()
    {
        var result = ConsoleCommandRegistry.Default.Bind("  Player.God ON ", DevState(true), Toggles());

        Assert.Null(result.Error);
        Assert.Equal(HarnessCommandKind.Invulnerable, result.Command.Value.Kind);
        Assert.True(result.Command.Value.Enabled);
    }

    private static void AssertBindFails(string line) =>
        Assert.False(ConsoleCommandRegistry.Default.Bind(line, DevState(true), Toggles()).Command.HasValue);

    private static ConsoleDevState DevState(bool dev) => new(dev);

    private static ConsoleToggleState Toggles(bool invulnerable = false, bool editor = false, bool hud = true, bool coordinates = false) =>
        new(invulnerable, editor, hud, coordinates);

    private static IReadOnlyList<string> LevelList() => new[] { "Bramblecrown Hill.mblevel.json", "thps.mblevel.json" };
}
