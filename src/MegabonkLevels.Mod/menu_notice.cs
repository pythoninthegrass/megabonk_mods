using Il2CppTMPro;
using UnityEngine;

namespace MegabonkLevels;

// A short message centred near the top of the screen, for refusals on the game's own menus where the editor toasts do not exist.
public static class MenuNotice
{
    private const float Seconds = 4f;
    private const float Width = 1400f;
    private const float Height = 70f;
    private const float FontSize = 30f;
    private const float TopOffset = 60f;

    private static GameObject _root;
    private static TextMeshProUGUI _label;
    private static float _expiry;

    public static void Show(string text)
    {
        if (_root == null)
        {
            Build();
        }

        _label.text = text;
        _root.SetActive(true);
        _expiry = Time.unscaledTime + Seconds;
    }

    public static void Tick()
    {
        if (_root != null && _root.activeSelf && Time.unscaledTime >= _expiry)
        {
            _root.SetActive(false);
        }
    }

    private static void Build()
    {
        _root = EditorUi.NewCanvas("MenuNotice");
        var (outer, _, _) = EditorUi.Bordered("Panel", _root.transform, EditorUi.PanelBorder, EditorUi.Gray(0.08f, 0.95f));
        outer.anchorMin = new Vector2(0.5f, 1f);
        outer.anchorMax = new Vector2(0.5f, 1f);
        outer.pivot = new Vector2(0.5f, 1f);
        outer.anchoredPosition = new Vector2(0f, -TopOffset);
        outer.sizeDelta = new Vector2(Width, Height);

        var textRect = EditorUi.NewRect("Text", outer);
        textRect.anchorMin = Vector2.zero;
        textRect.anchorMax = Vector2.one;
        textRect.offsetMin = Vector2.zero;
        textRect.offsetMax = Vector2.zero;
        _label = EditorUi.NewLabel(textRect, PositionLabel.FindFontAsset(EditorUi.FontName), TextAlignmentOptions.Center, FontSize);
    }
}
