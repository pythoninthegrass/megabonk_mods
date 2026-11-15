package content

import (
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func write(t *testing.T, path, text string) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

// packSource builds a synthetic pack directory for the pack validation tests.
func packSource(t *testing.T, packID string) string {
	t.Helper()
	source := filepath.Join(t.TempDir(), "packsrc", packID)
	if err := os.MkdirAll(source, 0o755); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(source, packID), "bundle bytes")
	write(t, filepath.Join(source, "manifest.json"),
		`{"id": "`+packID+`", "name": "THPS", "author": "user", "version": "1", "assets": ["a"]}`)
	write(t, filepath.Join(source, "attachments.json"), `{"schema":"pack-attachments/1"}`)
	return source
}

func setManifest(t *testing.T, source, text string) string {
	t.Helper()
	return write(t, filepath.Join(source, "manifest.json"), text)
}

func TestPathsMatchTheReference(t *testing.T) {
	cases := map[string]string{
		UserDataDir("/g"):        "/g/UserData",
		LevelsPath("/g"):         "/g/UserData/Levels",
		LevelPacksPath("/g"):     "/g/UserData/LevelPacks",
		PackDest("/g", "thps"):   "/g/UserData/LevelPacks/thps",
		RuntimePath("/g"):        "/g/dotnet6-win",
		VersionMarkerPath("/g"):  "/g/MelonLoader/MegabonkLevels.melonloader_version",
		RecordFilePath("/g"):     "/g/MegabonkLevels.installer.json",
		UserDataDir("/g/"):       "/g/UserData",
		PackDest("/g//", "thps"): "/g/UserData/LevelPacks/thps",
	}
	for got, want := range cases {
		if got != want {
			t.Errorf("got %q, want %q", got, want)
		}
	}
}

func TestIsBundleName(t *testing.T) {
	for name, want := range map[string]bool{
		"thps":           true,
		"thps.bundle":    true,
		"manifest.json":  false,
		"attachments.js": false,
		".hidden":        true,
		"level.dll":      false,
	} {
		if got := IsBundleName(name); got != want {
			t.Errorf("IsBundleName(%q) = %v, want %v", name, got, want)
		}
	}
}

func TestPackFilesPutsTheManifestFirstThenSortedBundles(t *testing.T) {
	source := packSource(t, "thps")
	write(t, filepath.Join(source, "sk8er.bundle"), "b")
	write(t, filepath.Join(source, "bones"), "b")
	write(t, filepath.Join(source, "notes.txt"), "text")
	names := []string{}
	for _, path := range PackFiles(source) {
		names = append(names, filepath.Base(path))
	}
	want := []string{"manifest.json", "attachments.json", "bones", "sk8er.bundle", "thps"}
	if !reflect.DeepEqual(names, want) {
		t.Errorf("PackFiles = %v, want %v", names, want)
	}
	if got := PackFiles(filepath.Join(t.TempDir(), "nothing")); len(got) != 0 {
		t.Errorf("PackFiles on a missing directory = %v", got)
	}
}

func TestValidatePackSourceAcceptsAGoodPack(t *testing.T) {
	if problems := ValidatePackSource(packSource(t, "thps")); len(problems) != 0 {
		t.Errorf("problems = %v", problems)
	}
}

func TestValidatePackSourceNamesEveryProblem(t *testing.T) {
	source := packSource(t, "thps")
	os.Remove(filepath.Join(source, "manifest.json"))
	want := source + "/manifest.json: a pack directory needs a manifest.json"
	if problems := ValidatePackSource(source); len(problems) != 1 || problems[0] != want {
		t.Errorf("problems = %v, want [%q]", problems, want)
	}
}

func TestValidatePackSourceManifestFieldErrors(t *testing.T) {
	cases := []struct {
		name    string
		text    string
		wantAny []string
		want    []string
	}{
		{
			name:    "missing fields",
			text:    `{"id": "thps", "name": "n"}`,
			wantAny: []string{"'author'", "'version'", "'assets'"},
		},
		{
			name: "id mismatch",
			text: `{"id": "other", "name": "n", "author": "a", "version": "1", "assets": []}`,
			want: []string{"manifest.json: manifest id 'other' does not match its pack folder 'thps'"},
		},
		{
			name: "assets not a list",
			text: `{"id": "thps", "name": "n", "author": "a", "version": "1", "assets": "a"}`,
			want: []string{"manifest.json: missing required array field 'assets'"},
		},
		{
			name: "blank author",
			text: `{"id": "thps", "name": "n", "author": "  ", "version": "1", "assets": []}`,
			want: []string{"manifest.json: missing required string field 'author'"},
		},
		{
			name: "attachments not a string",
			text: `{"id": "thps", "name": "n", "author": "a", "version": "1", "assets": [], "attachments": {}}`,
			want: []string{"manifest.json: 'attachments' must be a string when present"},
		},
		{
			name: "top level is a list",
			text: `[]`,
			want: []string{"manifest.json: the top level must be a JSON object"},
		},
	}
	for _, item := range cases {
		t.Run(item.name, func(t *testing.T) {
			source := packSource(t, "thps")
			setManifest(t, source, item.text)
			problems := ValidatePackSource(source)
			joined := strings.Join(problems, "\n")
			for _, want := range item.want {
				if !strings.Contains(joined, want) {
					t.Errorf("problems = %v, want %q", problems, want)
				}
			}
			if len(item.want) == 1 && len(problems) == 1 && problems[0] != item.want[0] {
				t.Errorf("problems = %v, want [%q]", problems, item.want[0])
			}
			for _, want := range item.wantAny {
				if !strings.Contains(joined, want) {
					t.Errorf("problems = %v, want one containing %q", problems, want)
				}
			}
		})
	}
}

func TestValidatePackSourceBundlesAndSidecar(t *testing.T) {
	source := packSource(t, "thps")
	os.Remove(filepath.Join(source, "thps"))
	problems := ValidatePackSource(source)
	want := source + ": no AssetBundle file — expected the bundle named after the pack id (or a .bundle file)"
	if len(problems) != 1 || problems[0] != want {
		t.Fatalf("problems = %v, want [%q]", problems, want)
	}
	write(t, filepath.Join(source, "thps.bundle"), "x")
	if problems := ValidatePackSource(source); len(problems) != 0 {
		t.Errorf("an explicit .bundle satisfies the check, got %v", problems)
	}

	source = packSource(t, "thps")
	write(t, filepath.Join(source, "attachments.json"), `{"schema":"nope"}`)
	problems = ValidatePackSource(source)
	if len(problems) != 1 || problems[0] != "attachments.json: expected a pack-attachments/1 document" {
		t.Errorf("problems = %v", problems)
	}
	write(t, filepath.Join(source, "attachments.json"), `{`)
	problems = ValidatePackSource(source)
	if len(problems) != 1 || !strings.HasPrefix(problems[0], "attachments.json: ") || problems[0] == "attachments.json: " {
		t.Errorf("problems = %v, want the sidecar named with a JSON error", problems)
	}
}

func TestValidatePackSourceFolderNameAndKind(t *testing.T) {
	missing := filepath.Join(t.TempDir(), "nope")
	if problems := ValidatePackSource(missing); len(problems) != 1 || problems[0] != missing+": no such directory" {
		t.Errorf("problems = %v", problems)
	}
	source := packSource(t, "thps")
	file := filepath.Join(source, "manifest.json")
	if problems := ValidatePackSource(file); len(problems) != 1 || problems[0] != file+": not a directory" {
		t.Errorf("problems = %v", problems)
	}
	bad := packSource(t, "Thps")
	if problems := ValidatePackSource(bad); len(problems) != 1 ||
		problems[0] != "pack folder name 'Thps': use a lowercase id of a-z, 0-9, '.', '_' or '-'" {
		t.Errorf("problems = %v", problems)
	}
}

func TestValidatePackSourceNamesAnOversizedFile(t *testing.T) {
	source := packSource(t, "thps")
	huge := filepath.Join(source, "huge")
	if err := os.WriteFile(huge, nil, 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.Truncate(huge, MaxFileBytes+1); err != nil {
		t.Fatal(err)
	}
	problems := ValidatePackSource(source)
	want := "huge: larger than the 256MB limit"
	if len(problems) != 1 || problems[0] != want {
		t.Errorf("problems = %v, want [%q]", problems, want)
	}
}

func TestValidateLevelFile(t *testing.T) {
	dir := t.TempDir()
	missing := filepath.Join(dir, "nope.mblevel.json")
	if problems := ValidateLevelFile(missing); len(problems) != 1 || problems[0] != missing+": no such file" {
		t.Errorf("missing = %v", problems)
	}
	if problems := ValidateLevelFile(dir); len(problems) != 1 || problems[0] != dir+": not a file" {
		t.Errorf("directory = %v", problems)
	}

	level := filepath.Join(dir, "level.mblevel.json")
	cases := []struct {
		text string
		want []string
	}{
		{`{"schema": 2}`, nil},
		{`{"schema": true}`, nil},
		{`[]`, []string{"level.mblevel.json: the top level must be a JSON object"}},
		{`{"schema": "2"}`, []string{"level.mblevel.json: 'schema' must be an integer"}},
		{`{"schema": 2.0}`, []string{"level.mblevel.json: 'schema' must be an integer"}},
		{`{"schema": 2,}`, []string{"level.mblevel.json: invalid JSON: "}},
		{`{`, []string{"level.mblevel.json: invalid JSON: "}},
	}
	for _, item := range cases {
		write(t, level, item.text)
		problems := ValidateLevelFile(level)
		if len(item.want) == 0 {
			if len(problems) != 0 {
				t.Errorf("ValidateLevelFile(%s) = %v, want none", item.text, problems)
			}
			continue
		}
		if len(problems) != 1 || !strings.HasPrefix(problems[0], item.want[0]) {
			t.Errorf("ValidateLevelFile(%s) = %v, want %v", item.text, problems, item.want)
		}
	}

	os.WriteFile(level, []byte{0xff, 0xfe}, 0o644)
	problems := ValidateLevelFile(level)
	if len(problems) != 1 || !strings.HasPrefix(problems[0], "level.mblevel.json: cannot be read as text: ") {
		t.Errorf("undecodable = %v", problems)
	}

	write(t, filepath.Join(dir, "plain.json"), "{}")
	problems = ValidateLevelFile(filepath.Join(dir, "plain.json"))
	if len(problems) != 1 || problems[0] != "plain.json: expected a .mblevel.json file" {
		t.Errorf("wrong name = %v", problems)
	}
	write(t, filepath.Join(dir, "l.level.json"), "{}")
	if problems := ValidateLevelFile(filepath.Join(dir, "l.level.json")); len(problems) != 0 {
		t.Errorf("the .level.json alias should pass, got %v", problems)
	}
}
