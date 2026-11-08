using System;
using System.Collections.Generic;
using System.Linq;
using Il2Cpp;
using Il2CppAssets.Scripts.Actors.Player;
using Il2CppAssets.Scripts.UI.Debug;
using Il2CppAssets.Scripts.Utility;
using Il2CppTMPro;
using MelonLoader;
using UnityEngine;
using UnityEngine.UI;

namespace MegabonkLevels;

// The Fallout-style console: a dark translucent panel that slides up from the bottom on the backquote key, pauses the
// run, and runs typed lines through the in-process harness. Input is read only through EditorInput; the slide advances
// on unscaled time so it animates while paused. See "In-game console" in docs/development.md.
public static class ConsoleOverlay
{
    private const float PanelHeightFraction = 0.4f;
    private const float SideMargin = 16f;
    private const float Padding = 10f;
    private const float LineHeight = 20f;
    private const float InputHeight = 30f;
    private const float InputGap = 6f;
    private const float FontSize = 16f;
    private const int MaxScrollbackLines = 400;
    private const int InputMaxLength = 512;
    private const KeyCode ToggleKey = KeyCode.BackQuote;

    private static readonly TextFieldModel _field = new(InputMaxLength);
    private static readonly ConsoleHistory _history = new();
    private static ConsoleScrollback _scrollback = new(MaxScrollbackLines, 1);
    private static readonly EditorCaretInput _caret = new();

    private static MelonLogger.Instance _logger;
    private static GameObject _root;
    private static RectTransform _panel;
    private static RectTransform _scrollRect;
    private static RectTransform _inputRect;
    private static TextMeshProUGUI[] _scrollLabels = Array.Empty<TextMeshProUGUI>();
    private static TextFieldView _inputView;
    private static ConsoleSlide _slide = ConsoleSlide.Parked;
    private static ConsoleEntryState? _entry;
    private static int _viewportLines = 1;

    public static bool Open { get; private set; }

    // True while the console owns the keyboard, so the mod's hotkeys and the game menu leave it alone.
    public static bool Focused => Open;

    public static bool CapturesKeyboard => Open;

    public static void Install(MelonLogger.Instance logger) => _logger = logger;

    public static void Toggle(MelonLogger.Instance logger)
    {
        _logger = logger;
        var decision = ConsoleState.Toggle(Open, DebugConsoleActive(), GameMenuOpen());
        if (decision == ConsoleToggle.Open)
        {
            OpenConsole();
        }
        else if (decision == ConsoleToggle.Close)
        {
            CloseConsole();
        }
    }

    // Called from the mod's OnUpdate every frame, whether or not the panel is open, so the toggle key and the slide run.
    public static void Tick()
    {
        _slide = ConsoleState.StepSlide(_slide, Open, Time.unscaledDeltaTime);

        if (!Open)
        {
            if (_root != null && !_slide.Moving)
            {
                _root.SetActive(false);
            }

            return;
        }

        _root.SetActive(true);
        ApplySlide();
        ReadInput();
        Render();
    }

    private static void OpenConsole()
    {
        var runActive = RunInProgress();
        _entry = new ConsoleEntryState(
            RunActive: runActive,
            Paused: MyTime.paused,
            CursorVisible: Cursor.visible,
            CursorLocked: Cursor.lockState != CursorLockMode.None);

        if (ConsoleState.ShouldPauseOnOpen(runActive))
        {
            MyTime.Pause();
        }

        Cursor.lockState = CursorLockMode.None;
        Cursor.visible = true;

        Build();
        _field.Clear();
        _history.Reset();
        _scrollback.Follow();
        Open = true;
        _slide = ConsoleState.StepSlide(_slide, true, 0f);
        _logger.Msg($"Console: opened, MyTime.paused={MyTime.paused}.");
    }

    private static void CloseConsole()
    {
        if (ConsoleState.ShouldUnpauseOnClose(_entry))
        {
            MyTime.Unpause();
        }

        if (ConsoleState.ShouldRestoreCursor(_entry) && _entry is { } state)
        {
            Cursor.visible = state.CursorVisible;
            Cursor.lockState = state.CursorLocked ? CursorLockMode.Locked : CursorLockMode.None;
        }

        _entry = null;
        Open = false;
        _logger.Msg($"Console: closed, MyTime.paused={MyTime.paused}.");
    }

    private static void ReadInput()
    {
        if (EditorInput.GetKeyDown(KeyCode.Escape))
        {
            CloseConsole();
            return;
        }

        var input = EditorInput.InputString;
        // The backquote that opened the console arrives as text on the same frame; drop it so it never lands in the line.
        if (input.Length > 0 && (input[0] == '`' || input[0] == '~'))
        {
            input = input.Substring(1);
        }

        _field.Navigate(_caret.Read());

        if (EditorInput.GetKeyDown(KeyCode.UpArrow))
        {
            _field.Set(_history.Previous());
        }
        else if (EditorInput.GetKeyDown(KeyCode.DownArrow))
        {
            _field.Set(_history.Next());
        }
        else if (EditorInput.GetKeyDown(KeyCode.Tab))
        {
            Complete();
        }
        else if (EditorInput.GetKeyDown(KeyCode.PageUp))
        {
            _scrollback.PageUp();
        }
        else if (EditorInput.GetKeyDown(KeyCode.PageDown))
        {
            _scrollback.PageDown();
        }
        else if (_field.Type(input))
        {
            Submit();
        }
    }

    private static void Complete()
    {
        var (head, prefix) = SplitWord(_field.Text, _field.Caret);
        var completion = ConsoleCommandRegistry.Default.Complete(prefix);
        if (completion.Matches.Count == 0)
        {
            return;
        }

        _field.Set(head + completion.Text + " ");
    }

    private static void Submit()
    {
        var line = _field.Text;
        var dev = ConsoleState.DevState(Environment.GetEnvironmentVariable);
        var toggles = CurrentToggles();
        var levels = SafeLevelList();
        var bind = ConsoleCommandRegistry.Default.Bind(line, dev, toggles, levels);
        var plan = ConsoleState.Plan(line, bind, Run);

        if (plan.ClearScrollback)
        {
            _scrollback.Clear();
        }

        foreach (var printed in plan.PrintLines)
        {
            _scrollback.Append(printed);
        }

        if (plan.RememberHistory)
        {
            _history.Add(line);
        }

        _scrollback.ScrollToBottom();
        _field.Clear();
    }

    // Runs one bound command in-process (the in-process harness entry point) and formats its result for scrollback.
    private static string Run(HarnessCommand command)
    {
        var result = DevHarness.Run(command);
        return ConsoleState.ReplyFor(result);
    }

    private static void Build()
    {
        if (_root != null)
        {
            return;
        }

        _root = EditorUi.NewCanvas("MegabonkLevelsConsole");
        var font = PositionLabel.FindFontAsset(EditorUi.FontName);
        _panel = EditorUi.Bordered("Console", _root.transform, EditorUi.PanelBorder, EditorUi.PanelFill).Outer;
        _panel.anchorMin = new Vector2(0f, 0f);
        _panel.anchorMax = new Vector2(1f, 0f);
        _panel.pivot = new Vector2(0.5f, 0f);
        _scrollRect = EditorUi.NewRect("Scrollback", _panel);

        Layout();

        var scrollFont = font;
        _scrollLabels = new TextMeshProUGUI[_viewportLines];
        for (var i = 0; i < _viewportLines; i++)
        {
            var row = EditorUi.NewRect($"Line{i}", _scrollRect);
            EditorUi.PlaceTopLeft(row, Padding, i * LineHeight, PanelWidth() - Padding * 2f, LineHeight);
            _scrollLabels[i] = EditorUi.NewLabel(row, scrollFont, TextAlignmentOptions.MidlineLeft, FontSize);
        }

        var input = EditorUi.Bordered("Input", _panel, EditorUi.SlotBorder, EditorUi.SearchFill);
        _inputRect = input.Outer;
        var inputText = EditorUi.NewRect("Text", _inputRect);
        inputText.anchorMin = Vector2.zero;
        inputText.anchorMax = Vector2.one;
        inputText.offsetMin = new Vector2(8f, 0f);
        inputText.offsetMax = new Vector2(-8f, 0f);
        var label = EditorUi.NewLabel(inputText, font, TextAlignmentOptions.MidlineLeft, FontSize);
        EditorUi.FixInputBaseline(label);
        _inputView = new TextFieldView(label);

        _scrollback = new ConsoleScrollback(MaxScrollbackLines, _viewportLines);
    }

    // Panel height and the scrollback/input rects depend on the screen, so re-measured each time the panel is shown.
    private static void Layout()
    {
        var height = Screen.height * PanelHeightFraction;
        _panel.sizeDelta = new Vector2(-SideMargin * 2f, height);
        _panel.anchoredPosition = new Vector2(0f, 0f);
        _viewportLines = Math.Max(1, Mathf.FloorToInt((height - Padding * 2f - InputHeight - InputGap) / LineHeight));
        EditorUi.PlaceTopLeft(_scrollRect, 0f, Padding, PanelWidth(), height - Padding * 2f - InputHeight - InputGap);
    }

    private static float PanelWidth() => Screen.width - SideMargin * 2f;

    private static void ApplySlide()
    {
        var height = Screen.height * PanelHeightFraction;
        _panel.anchoredPosition = new Vector2(0f, -(1f - _slide.Progress) * height);
    }

    private static void Render()
    {
        var visible = _scrollback.VisibleLines;
        // Bottom-align: the newest line sits on the last row, so a short buffer hugs the input rather than the top.
        var start = Math.Max(0, visible.Count - _viewportLines);
        for (var i = 0; i < _viewportLines; i++)
        {
            var index = start + i;
            _scrollLabels[i].text = index < visible.Count ? visible[index] : "";
        }

        var inputY = _panel.rect.height - InputHeight - Padding;
        _inputRect.anchoredPosition = new Vector2(Padding, -(inputY));
        _inputRect.sizeDelta = new Vector2(PanelWidth() - Padding * 2f, InputHeight);
        _inputView.Render(_field, true, "type a command, ~ to close");
    }

    public static IEnumerable<UiWidget> ListWidgets()
    {
        if (_root == null || !_root.activeInHierarchy)
        {
            return Enumerable.Empty<UiWidget>();
        }

        var widgets = new List<UiWidget?>
        {
            EditorUi.ToWidget("ConsoleInput", _inputRect),
            EditorUi.ToWidget("ConsoleScrollback", _scrollRect),
            EditorUi.ToWidget("ConsolePanel", _panel),
        };
        return widgets.Where(widget => widget.HasValue).Select(widget => widget.Value);
    }

    private static (string Head, string Prefix) SplitWord(string text, int caret)
    {
        var start = caret;
        while (start > 0 && !char.IsWhiteSpace(text[start - 1]))
        {
            start--;
        }

        return (text.Substring(0, start), text.Substring(start, caret - start));
    }

    private static ConsoleToggleState CurrentToggles() =>
        ConsoleState.Toggles(
            () => PlayerInvulnerability.Active,
            () => EditorMode.Active,
            () => HudVisible(),
            () => PositionLabel.Enabled);

    private static bool HudVisible() => UiManager.Instance == null || (UiManager.Instance.hudGroup?.alpha ?? 0f) > 0f;

    private static IReadOnlyList<string> SafeLevelList()
    {
        try
        {
            return LiveEditPatch.ListLevelFiles();
        }
        catch (Exception)
        {
            return Array.Empty<string>();
        }
    }

    private static bool DebugConsoleActive() => DebugConsole.Instance != null && DebugConsole.Instance.IsActive();

    // The game's own pause menu, distinct from MyTime.paused: while it is up it owns input the way DebugConsole does.
    private static bool GameMenuOpen()
    {
        var pause = UnityEngine.Object.FindObjectOfType<PauseUi>();
        return pause != null && pause.isActiveAndEnabled && pause.main != null && pause.main.activeInHierarchy;
    }

    private static bool RunInProgress() => MyPlayer.Instance != null && PlayerCamera.Instance != null;
}
