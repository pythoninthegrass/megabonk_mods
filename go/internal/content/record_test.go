package content

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func fullRecord() *Record {
	return &Record{
		Schema:         RecordSchema,
		PackageID:      "megabonk-levels-0.0.1-bepinex6.0.788-linux",
		ModVersion:     "0.0.1",
		BepinexVersion: "6.0.788",
		GameBuildID:    "21750826",
		InstalledAt:    "2026-11-01T10:00:00Z",
		GameDir:        "/game",
		Levels: map[string]LevelRecord{
			"warehouse": {Code: "warehouse", Filename: "UserData/Levels/warehouse.mblevel.json",
				Cover: "UserData/Levels/warehouse.png", Biome: "UserData/Levels/warehouse.biome.png"},
			"quiet": {Code: "quiet", Filename: "UserData/Levels/quiet.mblevel.json"},
		},
		Packs: map[string]PackRecord{
			"thps": {Version: "1.2.0", Dir: "UserData/LevelPacks/thps",
				Files: []string{"UserData/LevelPacks/thps/manifest.json", "UserData/LevelPacks/thps/thps"}},
			"sk8er": {Dir: "UserData/LevelPacks/sk8er"},
		},
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
	for _, key := range []string{"mod_version", "bepinex_version", "levels", "packs"} {
		if shaped[key] == nil {
			t.Errorf("%s missing: %v", key, shaped)
		}
	}

	loaded := LoadRecord(game)
	if loaded == nil {
		t.Fatal("LoadRecord = nil")
	}
	if !reflect.DeepEqual(loaded, fullRecord()) {
		t.Errorf("the round trip changed the record:\ngot  %+v\nwant %+v", loaded, fullRecord())
	}
	if !loaded.HasLevel("warehouse") || loaded.HasLevel("nope") {
		t.Errorf("HasLevel = %+v", loaded.Levels)
	}
	if !loaded.HasPack("thps") || loaded.HasPack("nope") {
		t.Errorf("HasPack = %+v", loaded.Packs)
	}
	if got := loaded.LevelCodes(); !reflect.DeepEqual(got, []string{"quiet", "warehouse"}) {
		t.Errorf("LevelCodes = %v", got)
	}
	if got := loaded.PackIDs(); !reflect.DeepEqual(got, []string{"sk8er", "thps"}) {
		t.Errorf("PackIDs = %v", got)
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

func TestSaveRecordCreatesTheGameDirectory(t *testing.T) {
	game := filepath.Join(t.TempDir(), "common", "Megabonk")
	if _, err := SaveRecord(game, &Record{Schema: RecordSchema}); err != nil {
		t.Fatal(err)
	}
	if !ppathIsFile(filepath.Join(game, RecordName)) {
		t.Error("SaveRecord should create the directory it writes the record into")
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
	if record.Levels != nil || record.Packs != nil {
		t.Errorf("an absent map should stay absent: %+v", record)
	}
}

func TestLoadRecordReadsWhatTheInstallerWrites(t *testing.T) {
	game := t.TempDir()
	write(t, filepath.Join(game, RecordName), `{
  "bepinex_version": "6.0.788",
  "game_buildid": "21750826",
  "game_dir": "/game",
  "installed_at": "2026-11-01T10:00:00Z",
  "installed_game_buildid": null,
  "levels": {
    "warehouse": {"biome": "UserData/Levels/warehouse.biome.png", "code": "warehouse", "cover": "UserData/Levels/warehouse.png", "filename": "UserData/Levels/warehouse.mblevel.json"},
    "quiet": {"code": "quiet", "filename": "UserData/Levels/quiet.mblevel.json"}
  },
  "mod_version": "0.0.1",
  "package_id": "megabonk-levels-0.0.1-bepinex6.0.788-linux",
  "packs": {"thps": {"dir": "UserData/LevelPacks/thps", "files": ["UserData/LevelPacks/thps/thps"], "version": "1.2.0"}},
  "schema": "megabonk-levels-install/2"
}
`)
	record := LoadRecord(game)
	if record == nil {
		t.Fatal("LoadRecord = nil")
	}
	if record.GameBuildID != "21750826" || record.BepinexVersion != "6.0.788" || record.ModVersion != "0.0.1" {
		t.Errorf("identity = %+v", record)
	}
	if record.InstalledGameBuildID != nil {
		t.Errorf("installed_game_buildid = %v", record.InstalledGameBuildID)
	}
	if record.Levels["warehouse"].Biome != "UserData/Levels/warehouse.biome.png" ||
		record.Levels["quiet"].Cover != "" {
		t.Errorf("levels = %+v", record.Levels)
	}
	if record.Packs["thps"].Version != "1.2.0" ||
		!reflect.DeepEqual(record.Packs["thps"].Files, []string{"UserData/LevelPacks/thps/thps"}) {
		t.Errorf("packs = %+v", record.Packs)
	}
}

func TestLoadRecordKeepsAReportedInstalledBuild(t *testing.T) {
	game := t.TempDir()
	write(t, filepath.Join(game, RecordName), `{"installed_game_buildid": "21900001"}`)
	record := LoadRecord(game)
	if record == nil || record.InstalledGameBuildID == nil || *record.InstalledGameBuildID != "21900001" {
		t.Errorf("record = %+v", record)
	}
}

func TestDescribeRecord(t *testing.T) {
	want := []string{
		"package megabonk-levels-0.0.1-bepinex6.0.788-linux",
		"mod 0.0.1 / BepInEx 6.0.788",
		"installed 2026-11-01T10:00:00Z",
		"2 level(s): quiet, warehouse",
		"packs: sk8er ?, thps 1.2.0",
	}
	if got := DescribeRecord(fullRecord()); !reflect.DeepEqual(got, want) {
		t.Errorf("DescribeRecord =\n%v\nwant\n%v", got, want)
	}

	if got := DescribeRecord(nil); !reflect.DeepEqual(got, []string{
		"package unknown", "mod ? / BepInEx ?", "0 level(s)", "0 pack(s)",
	}) {
		t.Errorf("empty = %v", got)
	}

	many := &Record{Levels: map[string]LevelRecord{}}
	for _, code := range []string{"a", "b", "c", "d", "e", "f", "g", "h"} {
		many.Levels[code] = LevelRecord{Code: code, Filename: "UserData/Levels/" + code + ".mblevel.json"}
	}
	lines := DescribeRecord(many)
	if lines[2] != "8 level(s): a, b, c, d, e, f, +2 more" {
		t.Errorf("a long level list = %q", lines[2])
	}
}

func TestRecordHelpersOnNil(t *testing.T) {
	var record *Record
	if record.HasLevel("a") || record.HasPack("a") || record.LevelCodes() != nil || record.PackIDs() != nil {
		t.Error("a nil record reads as nothing installed")
	}
}
