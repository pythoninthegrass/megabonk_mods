using Il2CppTMPro;
using UnityEngine;
using UnityEngine.UI;

namespace MegabonkLevels;

// Draws a TextFieldModel into a fixed-width monospace label: scrolls horizontally to keep the caret visible and draws a blinking caret.
public sealed class TextFieldView
{
    private const float CaretWidth = 2f;
    private const float BlinkPerSecond = 2f;
    // The label is baseline-aligned, so glyphs sit above the rect centre; lift the caret to match.
    private const float CaretLift = 0.3f;

    private readonly TextMeshProUGUI _label;
    private readonly RectTransform _caret;
    private float _charWidth;
    private int _start;

    public TextFieldView(TextMeshProUGUI label)
    {
        _label = label;
        _label.overflowMode = TextOverflowModes.Overflow;
        _caret = EditorUi.NewRect("Caret", label.rectTransform);
        _caret.anchorMin = new Vector2(0f, 0.5f);
        _caret.anchorMax = new Vector2(0f, 0.5f);
        _caret.pivot = new Vector2(0f, 0.5f);
        _caret.sizeDelta = new Vector2(CaretWidth, label.fontSize);
        var image = _caret.gameObject.AddComponent<Image>();
        image.color = Color.white;
        image.raycastTarget = false;
    }

    // placeholder replaces the text while it is empty; pass null when a separate placeholder label exists.
    public void Render(TextFieldModel model, bool focused, string placeholder)
    {
        if (_charWidth <= 0f)
        {
            _charWidth = _label.GetPreferredValues("0000000000").x / 10f;
        }

        var capacity = Mathf.Max(1, Mathf.FloorToInt(_label.rectTransform.rect.width / _charWidth));
        _start = TextWindow.Start(model.Caret, model.Text.Length, capacity, _start);
        _label.text = model.Text.Length == 0 ? placeholder ?? "" : TextWindow.Visible(model.Text, _start, capacity);
        _caret.anchoredPosition = new Vector2((model.Caret - _start) * _charWidth, _label.fontSize * CaretLift);
        _caret.gameObject.SetActive(focused && (int)(Time.unscaledTime * BlinkPerSecond) % 2 == 0);
    }
}
