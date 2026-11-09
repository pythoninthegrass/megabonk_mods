package content

import (
	"encoding/json"
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

func fullRecord() *Record {
	launchOption := "DOTNET_ROOT=..."
	prefix := "/prefix"
	via := "proton-ge"
	return &Record{
		Schema:             RecordSchema,
		PackageID:          "megabonk-levels-0.0.1-ml0.7.3-linux",
		ModVersion:         "0.0.1",
		MelonloaderVersion: "0.7.3",
		GameBuildID:        "21750826",
		InstalledAt:        "2026-11-01T10:00:00Z",
		GameDir:            "/game",
		Files:              []string{"Mods/MegabonkLevels.Mod.dll", "Mods/NLayer.dll", "UserLibs/NLayer.dll"},
		Levels:             []string{"UserData/Levels/a.mblevel.json"},
		Packs:              map[string]PackEntry{"thps": {Files: []string{"UserData/LevelPacks/thps/thps"}, Dir: "UserData/LevelPacks/thps"}, "sk8er": {}},
		Runtime:            &Runtime{Mode: "prefix", Path: "/prefix/drive_c/Program Files/dotnet", Version: "6.0.36", LaunchOption: &launchOption},
		DllOverride:        &DllOverride{Applied: true, Name: "version", Value: "native,builtin", Prefix: &prefix, Via: &via},
	}
}

func TestRecordRoundTrip(t *testing.T) {
	game := t.TempDir()
	if LoadRecord(game) != nil {
		t.Fatal("a vanilla directory has no record")
	}
	path, err := SaveRecord(game, fullRecord())
	if err != nil {
		t.Fatal(err)
	}
	if path != filepath.ToSlash(game)+"/"+RecordName {
		t.Errorf("SaveRecord returned %q", path)
	}
	raw, err := os.ReadFile(filepath.Join(game, RecordName))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(string(raw), "{\n  \"schema\": ") || !strings.HasSuffix(string(raw), "}\n") {
		t.Errorf("record is not indent-2 JSON with a trailing newline:\n%s", raw)
	}
	if strings.Contains(string(raw), `\u0026`) {
		t.Errorf("record escapes HTML characters:\n%s", raw)
	}
	var shaped map[string]any
	if err := json.Unmarshal(raw, &shaped); err != nil {
		t.Fatalf("the record is not JSON the reference can read: %v", err)
	}
	if shaped["dll_override"] == nil || shaped["runtime"] == nil {
		t.Errorf("runtime/dll_override missing: %v", shaped)
	}

	loaded := LoadRecord(game)
	if loaded == nil {
		t.Fatal("LoadRecord = nil")
	}
	if loaded.PackageID != "megabonk-levels-0.0.1-ml0.7.3-linux" || len(loaded.Files) != 3 {
		t.Errorf("loaded = %+v", loaded)
	}
	if loaded.Runtime == nil || loaded.Runtime.Version != "6.0.36" {
		t.Errorf("runtime = %+v", loaded.Runtime)
	}
	if loaded.DllOverride == nil || !loaded.DllOverride.Applied {
		t.Errorf("dll_override = %+v", loaded.DllOverride)
	}
	if loaded.Packs["thps"].Dir != "UserData/LevelPacks/thps" {
		t.Errorf("packs = %+v", loaded.Packs)
	}

	if err := ClearRecord(game); err != nil {
		t.Fatal(err)
	}
	if LoadRecord(game) != nil {
		t.Error("the record survived ClearRecord")
	}
	if err := ClearRecord(game); err != nil {
		t.Errorf("ClearRecord on a missing record should be a no-op, got %v", err)
	}
}

func TestLoadRecordIgnoresGarbage(t *testing.T) {
	game := t.TempDir()
	for _, text := range []string{"{", `[]`, `"a string"`, `null`, `3`} {
		write(t, filepath.Join(game, RecordName), text)
		if LoadRecord(game) != nil {
			t.Errorf("LoadRecord(%s) should be nil", text)
		}
	}
	write(t, filepath.Join(game, RecordName), `{"package_id": "x"}`)
	record := LoadRecord(game)
	if record == nil || record.PackageID != "x" {
		t.Errorf("a real record should load, got %+v", record)
	}
}

func TestLoadRecordReadsWhatThePythonReferenceWrites(t *testing.T) {
	game := t.TempDir()
	write(t, filepath.Join(game, RecordName), `{
  "dll_override": {"applied": false, "name": "version", "prefix": null, "value": "native,builtin", "via": null},
  "files": ["Mods/MegabonkLevels.Mod.dll"],
  "game_buildid": "21750826",
  "game_dir": "/game",
  "installed_at": "2026-11-01T10:00:00Z",
  "levels": [],
  "melonloader_version": "0.7.3",
  "mod_version": "0.0.1",
  "package_id": "megabonk-levels-0.0.1-ml0.7.3-linux",
  "packs": {"thps": {"dir": "UserData/LevelPacks/thps", "files": ["UserData/LevelPacks/thps/thps"]}},
  "runtime": {"launch_option": null, "mode": "gamedir", "path": "/game/dotnet6-win", "version": "6.0.36"},
  "schema": "megabonk-levels-install/1"
}
`)
	record := LoadRecord(game)
	if record == nil {
		t.Fatal("LoadRecord = nil")
	}
	if record.GameBuildID != "21750826" || record.MelonloaderVersion != "0.7.3" {
		t.Errorf("identity = %+v", record)
	}
	if record.Runtime == nil || record.Runtime.Mode != "gamedir" || record.Runtime.LaunchOption != nil {
		t.Errorf("runtime = %+v", record.Runtime)
	}
	if record.DllOverride == nil || record.DllOverride.Applied || record.DllOverride.Prefix != nil ||
		record.DllOverride.Via != nil || record.DllOverride.Value != "native,builtin" {
		t.Errorf("dll_override = %+v", record.DllOverride)
	}
	if record.Packs["thps"].Dir != "UserData/LevelPacks/thps" ||
		!reflect.DeepEqual(record.Packs["thps"].Files, []string{"UserData/LevelPacks/thps/thps"}) {
		t.Errorf("packs = %+v", record.Packs)
	}
	if len(record.Levels) != 0 {
		t.Errorf("levels = %v", record.Levels)
	}
}

func TestInstalledLoaderVersion(t *testing.T) {
	game := t.TempDir()
	if got := InstalledLoaderVersion(game); got != "" {
		t.Errorf("no marker = %q", got)
	}
	if HasInstalledLoaderVersion(game) {
		t.Error("a missing marker should not count as installed")
	}
	write(t, filepath.Join(game, "MelonLoader", "MegabonkLevels.melonloader_version"), " 0.7.3 \n")
	if got := InstalledLoaderVersion(game); got != "0.7.3" {
		t.Errorf("marker = %q", got)
	}
	if !HasInstalledLoaderVersion(game) {
		t.Error("a marker that exists should count as installed")
	}
}

func TestDescribeRecord(t *testing.T) {
	want := []string{
		"package megabonk-levels-0.0.1-ml0.7.3-linux",
		"mod 0.0.1 / MelonLoader 0.7.3",
		"installed 2026-11-01T10:00:00Z",
		".NET 6.0.36 in prefix at /prefix/drive_c/Program Files/dotnet",
		"version.dll override: native,builtin via proton-ge",
		"3 mod file(s)",
		"packs: sk8er, thps",
		"1 level file(s)",
	}
	if got := DescribeRecord(fullRecord()); !reflect.DeepEqual(got, want) {
		t.Errorf("DescribeRecord =\n%v\nwant\n%v", got, want)
	}

	sparse := &Record{
		PackageID:          "megabonk-levels-0.0.1-ml0.7.3-linux",
		ModVersion:         "0.0.1",
		MelonloaderVersion: "0.7.3",
		Files:              []string{"a", "b", "c"},
		DllOverride:        &DllOverride{},
	}
	want = []string{
		"package megabonk-levels-0.0.1-ml0.7.3-linux",
		"mod 0.0.1 / MelonLoader 0.7.3",
		"version.dll override: not set",
		"3 mod file(s)",
	}
	if got := DescribeRecord(sparse); !reflect.DeepEqual(got, want) {
		t.Errorf("sparse =\n%v\nwant\n%v", got, want)
	}

	if got := DescribeRecord(nil); !reflect.DeepEqual(got, []string{"package unknown", "mod ? / MelonLoader ?", "0 mod file(s)"}) {
		t.Errorf("empty = %v", got)
	}

	blankVia := &Record{DllOverride: &DllOverride{Applied: true, Value: "v"}}
	want = []string{"package unknown", "mod ? / MelonLoader ?", "version.dll override: v via unknown", "0 mod file(s)"}
	if got := DescribeRecord(blankVia); !reflect.DeepEqual(got, want) {
		t.Errorf("blank via = %v, want %v", got, want)
	}
}
