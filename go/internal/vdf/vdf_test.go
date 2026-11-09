package vdf

import (
	"reflect"
	"strings"
	"testing"
)

const libraryfolders = `
"libraryfolders"
{
	"0"
	{
		"path"		"/home/user/.local/share/Steam"
		"label"		""
		"apps"
		{
			"200710"		"2240977307"
			"3405340"		"522734781"
		}
	}
	"1"
	{
		"path"		"/media/sdcard/SteamLibrary"
		"apps"
		{
			"3405340"		"522734781"
		}
	}
}
`

const localconfig = `
"UserStats"
{
}
"apps"
{
	"3405340"
	{
		"LaunchOptions"		"PROTON_LOG=1 %command%"
		"CompatForceTool"		"proton_10"
	}
	"538030"
	{
		"LaunchOptions"		""
	}
}
`

func mustParse(t *testing.T, text string) *Dict {
	t.Helper()
	data, err := Parse(text)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	return data
}

func dictAt(t *testing.T, data *Dict, keys ...string) *Dict {
	t.Helper()
	node := data
	for _, key := range keys {
		value, ok := node.Get(key)
		if !ok {
			t.Fatalf("missing key %q", key)
		}
		child, ok := value.(*Dict)
		if !ok {
			t.Fatalf("value at %q is not a dict", key)
		}
		node = child
	}
	return node
}

func stringAt(t *testing.T, data *Dict, keys ...string) string {
	t.Helper()
	last := keys[len(keys)-1]
	node := dictAt(t, data, keys[:len(keys)-1]...)
	value, ok := node.Get(last)
	if !ok {
		t.Fatalf("missing key %q", last)
	}
	text, ok := value.(string)
	if !ok {
		t.Fatalf("value at %q is not a string", last)
	}
	return text
}

func TestParseReadsNestedSectionsAndValues(t *testing.T) {
	data := mustParse(t, libraryfolders)
	if got := stringAt(t, data, "libraryfolders", "0", "path"); got != "/home/user/.local/share/Steam" {
		t.Errorf("first path = %q", got)
	}
	if got := stringAt(t, data, "libraryfolders", "1", "path"); got != "/media/sdcard/SteamLibrary" {
		t.Errorf("second path = %q", got)
	}
	if got := stringAt(t, data, "libraryfolders", "0", "apps", "3405340"); got != "522734781" {
		t.Errorf("app id = %q", got)
	}
}

func TestParseKeepsEmptyStringValue(t *testing.T) {
	data := mustParse(t, libraryfolders)
	if got := stringAt(t, data, "libraryfolders", "0", "label"); got != "" {
		t.Errorf("label = %q", got)
	}
}

func TestParseAcceptsBareWordValues(t *testing.T) {
	data := mustParse(t, "\"root\"\n{\n\t\"a\"\t\t1\n\t\"b\"\t\ttrue\n}\n")
	if got := stringAt(t, data, "root", "a"); got != "1" {
		t.Errorf("a = %q", got)
	}
	if got := stringAt(t, data, "root", "b"); got != "true" {
		t.Errorf("b = %q", got)
	}
}

func TestParseIgnoresCommentsAndBlankLines(t *testing.T) {
	data := mustParse(t, "// note\n\n\"root\"\n{\n\t\"a\"\t\"b\"\n}\n")
	if got := data.Keys(); !reflect.DeepEqual(got, []string{"root"}) {
		t.Fatalf("keys = %v", got)
	}
	if got := stringAt(t, data, "root", "a"); got != "b" {
		t.Errorf("a = %q", got)
	}
}

func TestFindAllReturnsEveryWildcardHit(t *testing.T) {
	data := mustParse(t, libraryfolders)
	got := FindAll(data, []string{"libraryfolders", "*", "path"})
	want := []any{"/home/user/.local/share/Steam", "/media/sdcard/SteamLibrary"}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("FindAll = %v, want %v", got, want)
	}
}

func TestFindAllMissingKeyGivesEmptyList(t *testing.T) {
	data := mustParse(t, libraryfolders)
	if got := FindAll(data, []string{"libraryfolders", "*", "nope"}); len(got) != 0 {
		t.Errorf("FindAll = %v, want empty", got)
	}
}

func TestFindAllThroughAScalarReturnsEmpty(t *testing.T) {
	data := mustParse(t, libraryfolders)
	if got := FindAll(data, []string{"libraryfolders", "0", "path", "x"}); len(got) != 0 {
		t.Errorf("FindAll = %v, want empty", got)
	}
}

func TestLaunchOptionsForApp(t *testing.T) {
	data := mustParse(t, localconfig)
	if got, ok := LaunchOptions(data, "3405340"); !ok || got != "PROTON_LOG=1 %command%" {
		t.Errorf("LaunchOptions = %q, %v", got, ok)
	}
}

func TestLaunchOptionsNoneWhenAppAbsent(t *testing.T) {
	data := mustParse(t, localconfig)
	if _, ok := LaunchOptions(data, "999999"); ok {
		t.Error("expected no launch options")
	}
}

func TestLaunchOptionsNoneWhenEmpty(t *testing.T) {
	data := mustParse(t, localconfig)
	if _, ok := LaunchOptions(data, "538030"); ok {
		t.Error("expected empty launch options to read as none")
	}
}

func TestCompatForceToolForApp(t *testing.T) {
	data := mustParse(t, localconfig)
	if got, ok := CompatForceTool(data, "3405340"); !ok || got != "proton_10" {
		t.Errorf("CompatForceTool = %q, %v", got, ok)
	}
	if _, ok := CompatForceTool(data, "538030"); ok {
		t.Error("expected no forced tool")
	}
}

func TestLaunchOptionsSearchedUnderSteamAppsAndTopLevelApps(t *testing.T) {
	data := mustParse(t, "\"Steam\"\n{\n\t\"apps\"\n\t{\n\t\t\"7\"\n\t\t{\n\t\t\t\"LaunchOptions\"\t\t\"x %command%\"\n\t\t}\n\t}\n}\n")
	if got, ok := LaunchOptions(data, "7"); !ok || got != "x %command%" {
		t.Errorf("LaunchOptions = %q, %v", got, ok)
	}
}

func TestParseRaisesOnUnbalancedBrace(t *testing.T) {
	if _, err := Parse("\"root\"\n{\n\t\"a\"\t\"b\"\n"); err == nil {
		t.Fatal("expected an error on unbalanced braces")
	} else if err.Error() != "unexpected end of file: missing '}'" {
		t.Errorf("error = %q", err.Error())
	}
}

// The message has to name the key and the reason; the quoting style is free
// under the semantic-parity contract, so either one is accepted.
func TestParseReportsAKeyWithoutAValue(t *testing.T) {
	_, err := Parse("\"root\"\n{\n\t\"a\"\n}\n")
	if err == nil || (err.Error() != `key 'a' has no value` && err.Error() != `key "a" has no value`) {
		t.Errorf("error = %v", err)
	}
	if _, err := Parse("\"a\" \"b\" }"); err == nil || err.Error() != "unexpected '}'" {
		t.Errorf("error = %v", err)
	}
	if _, err := Parse("{ \"a\": 1 }"); err == nil || err.Error() != "'{' without a key" {
		t.Errorf("error = %v", err)
	}
	if _, err := Parse("\"a\" \"unterminated"); err == nil || err.Error() != "unterminated quoted string" {
		t.Errorf("error = %v", err)
	}
}

func TestParseUnescapesQuotesInsideStrings(t *testing.T) {
	data := mustParse(t, "\"root\"\n{\n\t\"a\"\t\"say \\\"hi\\\"\"\n}\n")
	if got := stringAt(t, data, "root", "a"); got != `say "hi"` {
		t.Errorf("a = %q", got)
	}
}

func TestSemicolonWordEndsTokenizingLikePython(t *testing.T) {
	data := mustParse(t, "\"root\"\n{\n\t\"a\"\t\"b\"\n}\n; trailing junk that would not parse\n")
	if got := stringAt(t, data, "root", "a"); got != "b" {
		t.Errorf("a = %q", got)
	}
}

func TestToValidUTF8ReplacesOneRunePerBadByte(t *testing.T) {
	got := ToValidUTF8("a\xff\xffe")
	if !strings.Contains(got, "a") || strings.Count(got, "\ufffd") != 2 {
		t.Errorf("ToValidUTF8 = %q", got)
	}
}
