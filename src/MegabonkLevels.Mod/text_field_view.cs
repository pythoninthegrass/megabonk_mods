using TMPro;
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
    private readonly bool _blockCaret;
    private float _charWidth;
    private int _start;

    // blockCaret draws a translucent cell-wide block over the character at the caret instead of a thin bar.
    public TextFieldView(TextMeshProUGUI label, bool blockCaret = false)
    {
        _label = label;
        _blockCaret = blockCaret;
        _label.overflowMode = TextOverflowModes.Overflow;
        _caret = EditorUi.NewRect("Caret", label.rectTransform);
        _caret.anchorMin = new Vector2(0f, 0.5f);
        _caret.anchorMax = new Vector2(0f, 0.5f);
        _caret.pivot = new Vector2(0f, 0.5f);
        _caret.sizeDelta = new Vector2(CaretWidth, label.fontSize);
        var image = _caret.gameObject.AddComponent<Image>();
        image.color = blockCaret ? new Color(1f, 1f, 1f, 0.55f) : Color.white;
        image.raycastTarget = false;
    }

    // placeholder replaces the text while it is empty; pass null when a separate placeholder label exists.
    public void Render(TextFieldModel model, bool focused, string placeholder)
    {
        if (_charWidth <= 0f)
        {
            _charWidth = _label.GetPreferredValues("0000000000").x / 10f;
            if (_blockCaret)
            {
                _caret.sizeDelta = new Vector2(_charWidth, _label.fontSize);
            }
        }

        var capacity = Mathf.Max(1, Mathf.FloorToInt(_label.rectTransform.rect.width / _charWidth));
        _start = TextWindow.Start(model.Caret, model.Text.Length, capacity, _start);
        _label.text = model.Text.Length == 0 ? placeholder ?? "" : TextWindow.Visible(model.Text, _start, capacity);
        _caret.anchoredPosition = new Vector2((model.Caret - _start) * _charWidth, _label.fontSize * CaretLift);
        _caret.gameObject.SetActive(focused && (int)(Time.unscaledTime * BlinkPerSecond) % 2 == 0);
    }
}
