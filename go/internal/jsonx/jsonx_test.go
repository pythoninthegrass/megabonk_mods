package jsonx

import (
	"encoding/json"
	"reflect"
	"testing"
)

func decodeOne(t *testing.T, text string) any {
	t.Helper()
	value, err := Decode(text)
	if err != nil {
		t.Fatalf("Decode(%s): %v", text, err)
	}
	return value
}

func TestDecodeKeepsNumbersAsWritten(t *testing.T) {
	document, ok := decodeOne(t, `{"int": 21750826, "float": 2.0, "exp": 1e3, "neg": -1}`).(map[string]any)
	if !ok {
		t.Fatal("not an object")
	}
	for key, want := range map[string]string{
		"int":   "21750826",
		"float": "2.0",
		"exp":   "1e3",
		"neg":   "-1",
	} {
		number, ok := document[key].(json.Number)
		if !ok {
			t.Errorf("%s = %#v, want a json.Number", key, document[key])
			continue
		}
		if number.String() != want {
			t.Errorf("%s = %q, want %q", key, number.String(), want)
		}
	}
	if !IsInt(document["int"]) || !IsInt(document["neg"]) {
		t.Errorf("integers should be integers: %v %v", document["int"], document["neg"])
	}
	for _, key := range []string{"float", "exp"} {
		if IsInt(document[key]) {
			t.Errorf("%s should not be an integer", key)
		}
	}
	if !IsInt(true) {
		t.Error("Python counts a bool as an int, and so should this")
	}
}

func TestDecodeRejectsTrailingContent(t *testing.T) {
	for _, text := range []string{`{} {}`, `[] 1`, `{"a": 1} ` + `{"b": 2}`} {
		if _, err := Decode(text); err == nil {
			t.Errorf("Decode(%s) should report extra data", text)
		}
	}
	if _, err := Decode("{}\n\n"); err != nil {
		t.Errorf("trailing whitespace is not extra data: %v", err)
	}
}

func TestDecodeRejectsMalformedJSON(t *testing.T) {
	for _, text := range []string{"{", `{"a": }`, `{"a": 1,}`, "", "nul"} {
		if _, err := Decode(text); err == nil {
			t.Errorf("Decode(%s) should fail", text)
		}
	}
}

func TestTextRendersScalarsLikeTheReference(t *testing.T) {
	cases := []struct {
		value any
		want  string
	}{
		{nil, "None"},
		{true, "True"},
		{false, "False"},
		{"linux", "linux"},
		{json.Number("21750826"), "21750826"},
		{json.Number("2.0"), "2.0"},
		{[]any{"a"}, `["a"]`},
	}
	for _, item := range cases {
		if got := Text(item.value); got != item.want {
			t.Errorf("Text(%#v) = %q, want %q", item.value, got, item.want)
		}
	}
}

func TestTruthyFollowsPython(t *testing.T) {
	truthy := []any{"a", true, []any{""}, map[string]any{"k": nil}, json.Number("1"), json.Number("-1"), json.Number("0.5")}
	for _, value := range truthy {
		if !Truthy(value) {
			t.Errorf("Truthy(%#v) = false", value)
		}
	}
	for _, value := range []any{nil, false, "", json.Number("0"), json.Number("0.0"), json.Number("0e0"), []any{}, map[string]any{}} {
		if Truthy(value) {
			t.Errorf("Truthy(%#v) = true", value)
		}
	}
}

func TestTypePredicates(t *testing.T) {
	if IsNonBlankString("  ") || IsNonBlankString("") || IsNonBlankString(nil) || IsNonBlankString(json.Number("1")) {
		t.Error("IsNonBlankString should reject blanks and non-strings")
	}
	if !IsNonBlankString(" thps ") {
		t.Error("IsNonBlankString should accept a padded string")
	}
	if !IsString("") || IsString(1) {
		t.Error("IsString is wrong")
	}
	if IsStringList(nil) {
		t.Error("a missing field is not a list")
	}
	items := decodeOne(t, `["a", "b"]`)
	if !IsStringList(items) {
		t.Errorf("IsStringList(%v) = false", items)
	}
	if IsStringList(decodeOne(t, `["a", 1]`)) {
		t.Error("a mixed list is not a string list")
	}
}

func TestLengthCountsContainersAndRunes(t *testing.T) {
	cases := []struct {
		value any
		want  int
	}{
		{nil, 0},
		{"café", 4},
		{[]any{1, 2}, 2},
		{map[string]any{"a": 1}, 1},
		{json.Number("7"), 0},
		{true, 0},
	}
	for _, item := range cases {
		if got := Length(item.value); got != item.want {
			t.Errorf("Length(%#v) = %d, want %d", item.value, got, item.want)
		}
	}
}

func TestAsMapAndAsList(t *testing.T) {
	object, ok := AsMap(decodeOne(t, `{"a": 1}`))
	if !ok || !reflect.DeepEqual(object, map[string]any{"a": json.Number("1")}) {
		t.Errorf("AsMap = %#v, %v", object, ok)
	}
	if _, ok := AsMap(decodeOne(t, `[]`)); ok {
		t.Error("an array is not an object")
	}
	if _, ok := AsList(decodeOne(t, `{}`)); ok {
		t.Error("an object is not an array")
	}
}
