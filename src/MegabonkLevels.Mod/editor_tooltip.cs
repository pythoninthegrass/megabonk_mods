using Il2CppTMPro;
using UnityEngine;
using UnityEngine.UI;

namespace MegabonkLevels;

// A text box that follows the pointer, shared by the palette and the toolbar.
public sealed class EditorTooltip
{
    private const float LabelMargin = 8f;
    private const float PointerOffset = 16f;
    private const float HoverSeconds = 3f;
    private const float GraceSeconds = 2f;

    private static readonly HoverActivity SharedActivity = new();

    private readonly RectTransform _rect;
    private readonly TextMeshProUGUI _label;

    public EditorTooltip(Transform parent, TMP_FontAsset font, float fontSize)
    {
        _rect = EditorUi.NewRect("Tooltip", parent);
        _rect.anchorMin = new Vector2(0f, 1f);
        _rect.anchorMax = new Vector2(0f, 1f);
        _rect.pivot = new Vector2(0f, 1f);
        _rect.gameObject.AddComponent<Image>().color = EditorUi.Gray(0.08f, 0.95f);

        var labelRect = EditorUi.NewRect("Label", _rect);
        labelRect.anchorMin = Vector2.zero;
        labelRect.anchorMax = Vector2.one;
        labelRect.offsetMin = new Vector2(LabelMargin, 0f);
        labelRect.offsetMax = new Vector2(-LabelMargin, 0f);
        _label = EditorUi.NewLabel(labelRect, font, TextAlignmentOptions.MidlineLeft, fontSize);
        _label.richText = false;
        _rect.gameObject.SetActive(false);
    }

    // Every tooltip waits HoverSeconds before showing, except within GraceSeconds of any tooltip having been visible.
    public static HoverDelay NewHoverDelay() => new(HoverSeconds, GraceSeconds, SharedActivity);

    public void Hide() => _rect.gameObject.SetActive(false);

    public void Show(string text, Vector2 mouse)
    {
        _label.text = text;
        var size = _label.GetPreferredValues(text) + new Vector2(LabelMargin * 2f, 12f);
        size.x = Mathf.Min(size.x, Screen.width);
        _rect.sizeDelta = size;
        var x = Mathf.Clamp(mouse.x + PointerOffset, 0f, Screen.width - size.x);
        var top = Mathf.Clamp(Screen.height - mouse.y + PointerOffset, 0f, Mathf.Max(0f, Screen.height - size.y));
        _rect.anchoredPosition = new Vector2(x, -top);
        _rect.gameObject.SetActive(true);
    }
}
