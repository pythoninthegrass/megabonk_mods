using System;
using System.Collections.Generic;
using System.Text.Json.Nodes;

namespace MegabonkLevels.Tests;

public class ConsoleStateTests
{
    private static ConsoleEntryState Entry(bool runActive = true, bool paused = false, bool cursorVisible = false, bool cursorLocked = true) =>
        new(runActive, paused, cursorVisible, cursorLocked);

    [Fact]
    public void Toggle_ClosesWhenOpen() =>
        Assert.Equal(ConsoleToggle.Close, ConsoleState.Toggle(open: true, devConsoleActive: false, gameMenuOpen: false));

    [Fact]
    public void Toggle_OpensWhenClosed() =>
        Assert.Equal(ConsoleToggle.Open, ConsoleState.Toggle(open: false, devConsoleActive: false, gameMenuOpen: false));

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void Toggle_StaysWhileTheGameDebugConsoleIsActive(bool open) =>
        Assert.Equal(ConsoleToggle.Stay, ConsoleState.Toggle(open, devConsoleActive: true, gameMenuOpen: false));

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void Toggle_StaysWhileTheGameMenuIsOpen(bool open) =>
        Assert.Equal(ConsoleToggle.Stay, ConsoleState.Toggle(open, devConsoleActive: false, gameMenuOpen: true));

    [Fact]
    public void Opening_PausesALiveRun() => Assert.True(ConsoleState.ShouldPauseOnOpen(runActive: true));

    [Fact]
    public void Opening_PausesNothingOnTheMainMenu() => Assert.False(ConsoleState.ShouldPauseOnOpen(runActive: false));

    [Fact]
    public void Closing_UnpausesARunTheConsolePaused() =>
        Assert.True(ConsoleState.ShouldUnpauseOnClose(Entry(paused: false)));

    [Fact]
    public void Closing_LeavesAnAlreadyFrozenRunFrozen() =>
        Assert.False(ConsoleState.ShouldUnpauseOnClose(Entry(paused: true)));

    [Fact]
    public void Closing_LeavesTheMainMenuUnpaused() =>
        Assert.False(ConsoleState.ShouldUnpauseOnClose(Entry(runActive: false)));

    [Fact]
    public void Closing_WithNoOpenEntry_RestoresNothing()
    {
        ConsoleEntryState? none = null;
        Assert.False(ConsoleState.ShouldUnpauseOnClose(none));
        Assert.False(ConsoleState.ShouldRestoreCursor(none));
    }

    [Fact]
    public void Closing_RestoresTheCursorItCaptured() => Assert.True(ConsoleState.ShouldRestoreCursor(Entry()));

    [Fact]
    public void Slide_FromParked_AnimatesUpOverTheFullDistance()
    {
        var slide = ConsoleSlide.Parked;
        var step = ConsoleState.SlideSeconds / 2f;

        slide = ConsoleState.StepSlide(slide, open: true, step);
        Assert.True(slide.Moving);
        Assert.Equal(0.5f, slide.Progress, 3);

        slide = ConsoleState.StepSlide(slide, open: true, step);
        Assert.False(slide.Moving);
        Assert.Equal(1f, slide.Progress, 3);
    }

    [Fact]
    public void Slide_ClosesBackToParked()
    {
        var slide = ConsoleSlide.Shown;
        var step = ConsoleState.SlideSeconds / 2f;

        slide = ConsoleState.StepSlide(slide, open: false, step);
        Assert.True(slide.Moving);
        Assert.Equal(0.5f, slide.Progress, 3);

        slide = ConsoleState.StepSlide(slide, open: false, step);
        Assert.False(slide.Moving);
        Assert.Equal(0f, slide.Progress, 3);
    }

    [Fact]
    public void Slide_OverLongStep_ClampsToTheTarget()
    {
        var up = ConsoleState.StepSlide(ConsoleSlide.Parked, open: true, ConsoleState.SlideSeconds * 4f);
        Assert.Equal(1f, up.Progress, 3);
        Assert.False(up.Moving);

        var down = ConsoleState.StepSlide(ConsoleSlide.Shown, open: false, ConsoleState.SlideSeconds * 4f);
        Assert.Equal(0f, down.Progress, 3);
        Assert.False(down.Moving);
    }

    [Fact]
    public void Slide_ReachedTargetAndAskedAgain_IsNotMoving()
    {
        Assert.False(ConsoleState.StepSlide(ConsoleSlide.Shown, open: true, 0.01f).Moving);
        Assert.False(ConsoleState.StepSlide(ConsoleSlide.Parked, open: false, 0.01f).Moving);
    }

    [Theory]
    [InlineData(0f)]
    [InlineData(-1f)]
    [InlineData(float.NaN)]
    public void Slide_ABadDeltaTime_MovesNothing(float dt)
    {
        var slide = ConsoleState.StepSlide(new ConsoleSlide(0.4f, true), open: true, dt);
        Assert.Equal(0.4f, slide.Progress, 3);
        Assert.False(slide.Moving);
    }

    [Theory]
    [InlineData("1", true)]
    [InlineData("true", true)]
    [InlineData("TRUE", true)]
    [InlineData("", false)]
    [InlineData("0", false)]
    [InlineData("nope", false)]
    public void DevState_ReflectsTheEnvironmentVariable(string value, bool expected) =>
        Assert.Equal(expected, ConsoleState.DevState(_ => value).DevEnabled);

    [Fact]
    public void DevState_ReadsTheDocumentedVariableName()
    {
        string? seen = null;
        ConsoleState.DevState(name =>
        {
            seen = name;
            return "1";
        });

        Assert.Equal("MEGABONK_DEV", seen);
    }

    [Fact]
    public void Toggles_ReadsEachCurrentState()
    {
        var toggles = ConsoleState.Toggles(() => true, () => false, () => true, () => false);
        Assert.True(toggles.Invulnerable);
        Assert.False(toggles.Editor);
        Assert.True(toggles.Hud);
        Assert.False(toggles.Coordinates);
    }

    [Fact]
    public void Plan_BlankLine_PrintsNothingAndRunsNothing()
    {
        var plan = ConsoleState.Plan("   ", new ConsoleBindResult(null, null, null), _ => "ok");

        Assert.Empty(plan.PrintLines);
        Assert.False(plan.ClearScrollback);
        Assert.False(plan.RememberHistory);
    }

    [Fact]
    public void Plan_RefusedLine_EchosTheLineAndTheReply()
    {
        var plan = ConsoleState.Plan("bogus", new ConsoleBindResult(null, null, "unknown verb 'bogus'"), _ => "ok");

        Assert.Equal(new[] { "> bogus", "unknown verb 'bogus'" }, plan.PrintLines);
        Assert.False(plan.ClearScrollback);
        Assert.False(plan.RememberHistory);
    }

    [Fact]
    public void Plan_ConsoleOnlyVerb_PrintsItsReplyAndRemembersHistory()
    {
        var plan = ConsoleState.Plan("help", new ConsoleBindResult(null, "state  list things", null), _ => "ok");

        Assert.Equal(new[] { "state  list things" }, plan.PrintLines);
        Assert.False(plan.ClearScrollback);
        Assert.True(plan.RememberHistory);
    }

    [Fact]
    public void Plan_ClearVerb_ClearsScrollbackAndAddsNoLine()
    {
        var plan = ConsoleState.Plan("clear", new ConsoleBindResult(null, "", null), _ => "ok");

        Assert.Empty(plan.PrintLines);
        Assert.True(plan.ClearScrollback);
        Assert.True(plan.RememberHistory);
    }

    [Fact]
    public void Plan_ClearBoundByTheRegistry_ClearsScrollbackOnly()
    {
        var bind = ConsoleCommandRegistry.Default.Bind("clear", new ConsoleDevState(false), new ConsoleToggleState(false, false, false, false));
        var plan = ConsoleState.Plan("clear", bind, _ => throw new InvalidOperationException("clear must not run a harness command"));

        Assert.True(plan.ClearScrollback);
        Assert.Empty(plan.PrintLines);
    }

    [Fact]
    public void Plan_HistoryVerb_ListsTheRememberedLinesNumbered()
    {
        var bind = new ConsoleBindResult(null, "", null, ListHistory: true);

        var plan = ConsoleState.Plan("history", bind, _ => "ok", new[] { "state", "editor on" });

        Assert.Equal(new[] { "  1  state", "  2  editor on" }, plan.PrintLines);
        Assert.False(plan.ClearScrollback);
        Assert.True(plan.RememberHistory);
    }

    [Fact]
    public void Plan_HistoryVerb_WithNoEntriesSaysSo()
    {
        var bind = new ConsoleBindResult(null, "", null, ListHistory: true);

        var plan = ConsoleState.Plan("history", bind, _ => "ok", Array.Empty<string>());

        Assert.Equal(new[] { "history is empty" }, plan.PrintLines);
        Assert.False(plan.ClearScrollback);
    }

    [Fact]
    public void Plan_HistoryVerb_WithoutAHistoryArgumentSaysItIsEmpty()
    {
        var bind = new ConsoleBindResult(null, "", null, ListHistory: true);

        var plan = ConsoleState.Plan("history", bind, _ => "ok");

        Assert.Equal(new[] { "history is empty" }, plan.PrintLines);
    }

    [Fact]
    public void Plan_BoundLine_RunsThroughTheCallbackAndEchoesTheReply()
    {
        var runs = new List<string>();
        var command = Harness("""{"command":"state"}""");
        var plan = ConsoleState.Plan("state", new ConsoleBindResult(command, null, null), run =>
        {
            runs.Add(run.Kind.ToString());
            return "editor: off";
        });

        Assert.Equal(new[] { "> state", "editor: off" }, plan.PrintLines);
        Assert.False(plan.ClearScrollback);
        Assert.True(plan.RememberHistory);
        Assert.Equal(new[] { "State" }, runs);
    }

    [Fact]
    public void ReplyFor_FailedResult_NamesTheError() =>
        Assert.Equal("error: no player", ConsoleState.ReplyFor(HarnessResult.Failure("state", "no player")));

    [Fact]
    public void ReplyFor_SuccessWithNoPayload_ReadsOk() =>
        Assert.Equal("ok", ConsoleState.ReplyFor(HarnessResult.Success("freeze", null)));

    [Fact]
    public void ReplyFor_SuccessWithPayload_PrintsTheJson()
    {
        var reply = ConsoleState.ReplyFor(HarnessResult.Success("state", new JsonObject { ["editor"] = true }));

        Assert.Equal("""{"editor":true}""", reply);
    }

    [Fact]
    public void ReplyFor_ResultWithAMessage_PrintsTheMessageInsteadOfTheJson()
    {
        var reply = ConsoleState.ReplyFor(HarnessResult.Success("music", new JsonObject { ["message"] = "1  a\n2  b", ["count"] = 2 }));

        Assert.Equal("1  a\n2  b", reply);
    }

    private static HarnessCommand Harness(string json)
    {
        Assert.True(HarnessCommand.TryParse(json, out var command, out var error), error);
        return command;
    }
}
