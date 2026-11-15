package content

import (
	"archive/zip"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func stagingZip(t *testing.T, name string, entries [][2]string) string {
	t.Helper()
	archive := filepath.Join(t.TempDir(), name)
	handle, err := os.Create(archive)
	if err != nil {
		t.Fatal(err)
	}
	writer := zip.NewWriter(handle)
	for _, entry := range entries {
		member, err := writer.Create(entry[0])
		if err != nil {
			t.Fatal(err)
		}
		if _, err := member.Write([]byte(entry[1])); err != nil {
			t.Fatal(err)
		}
	}
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}
	if err := handle.Close(); err != nil {
		t.Fatal(err)
	}
	return archive
}

func TestStagingWritesOnlyInsideItsFolder(t *testing.T) {
	root := t.TempDir()
	staging, err := NewStaging(root, "run")
	if err != nil {
		t.Fatal(err)
	}
	level := write(t, filepath.Join(t.TempDir(), "warehouse.mblevel.json"), `{"schema":2}`)
	if err := staging.WriteLevel("warehouse", level, "", ""); err != nil {
		t.Fatal(err)
	}
	archive := stagingZip(t, "thps.zip", [][2]string{
		{"thps/manifest.json", `{"id":"thps","name":"THPS","author":"a","version":"1","assets":["a"]}`},
		{"thps/thps", "bundle"},
	})
	if _, err := staging.InstallPack("thps", "1.0.0", archive); err != nil {
		t.Fatal(err)
	}

	for _, name := range []string{
		"UserData/Levels/warehouse.mblevel.json",
		"UserData/LevelPacks/thps/manifest.json",
		"UserData/LevelPacks/thps/thps",
	} {
		if !ppathIsFile(filepath.Join(staging.Dir, filepath.FromSlash(name))) {
			t.Errorf("%s was not staged", name)
		}
	}
	if ppathIsFile(filepath.Join(root, "UserData", "Levels", "warehouse.mblevel.json")) ||
		ppathIsDir(filepath.Join(root, "UserData", "LevelPacks")) {
		t.Error("staging wrote into the directory it is not meant to touch")
	}
	if staging.GameDir != filepath.ToSlash(root) {
		t.Errorf("GameDir = %q, want %q", staging.GameDir, filepath.ToSlash(root))
	}
}

func TestStagingCommitPlacesStagedFilesAndLeavesTheRest(t *testing.T) {
	game := t.TempDir()
	write(t, filepath.Join(game, "Megabonk.exe"), "MZ")
	own := filepath.Join(game, "UserData", "Levels", "mine.mblevel.json")
	write(t, own, `{"schema":2,"title":"Mine"}`)

	staging, err := NewStaging(game, "run")
	if err != nil {
		t.Fatal(err)
	}
	level := write(t, filepath.Join(t.TempDir(), "warehouse.mblevel.json"), `{"schema":2,"title":"Warehouse"}`)
	cover := write(t, filepath.Join(t.TempDir(), "whatever.png"), "cover bytes")
	if err := staging.WriteLevel("warehouse", level, cover, ""); err != nil {
		t.Fatal(err)
	}
	archive := stagingZip(t, "thps.zip", [][2]string{
		{"thps/manifest.json", `{"id":"thps","name":"THPS","author":"a","version":"1","assets":["a"]}`},
		{"thps/thps", "bundle"},
	})
	pack, err := staging.InstallPack("thps", "1.0.0", archive)
	if err != nil {
		t.Fatal(err)
	}

	placed, err := staging.Commit()
	if err != nil {
		t.Fatal(err)
	}
	want := []string{
		"UserData/LevelPacks/thps/manifest.json",
		"UserData/LevelPacks/thps/thps",
		"UserData/Levels/warehouse.mblevel.json",
		"UserData/Levels/warehouse.png",
	}
	if strings.Join(placed, ",") != strings.Join(want, ",") {
		t.Errorf("placed = %v, want %v", placed, want)
	}
	if !ppathIsFile(filepath.Join(game, filepath.FromSlash(want[0]))) ||
		!ppathIsFile(filepath.Join(game, filepath.FromSlash(want[2]))) ||
		!ppathIsFile(filepath.Join(game, filepath.FromSlash(want[3]))) {
		t.Errorf("the staged files did not land in the game directory")
	}
	if body, err := os.ReadFile(own); err != nil || !strings.Contains(string(body), "Mine") {
		t.Errorf("the player's own level was disturbed: %v %s", err, body)
	}
	if ppathIsDir(filepath.Join(staging.Dir, "UserData")) {
		t.Error("the staging folder survived the commit")
	}
	if ppathIsDir(filepath.Join(game, "staging")) {
		t.Error("the staging folder was left inside the game directory")
	}
	if pack.Dir != "UserData/LevelPacks/thps" {
		t.Errorf("pack dir = %q", pack.Dir)
	}
}

func TestStagingCommitReplacesADirectoryTheInstallerOwns(t *testing.T) {
	game := t.TempDir()
	stale := filepath.Join(game, "UserData", "LevelPacks", "thps", "stale.bundle")
	write(t, stale, "old bundle")

	staging, err := NewStaging(game, "run")
	if err != nil {
		t.Fatal(err)
	}
	archive := stagingZip(t, "thps.zip", [][2]string{
		{"thps/manifest.json", `{"id":"thps","name":"THPS","author":"a","version":"1","assets":["a"]}`},
		{"thps/thps", "bundle"},
	})
	if _, err := staging.InstallPack("thps", "1.0.0", archive); err != nil {
		t.Fatal(err)
	}
	if _, err := staging.Commit(); err != nil {
		t.Fatal(err)
	}
	if ppathIsFile(stale) {
		t.Error("a folder this installer owns is replaced wholesale, not merged into")
	}
}

func TestStagingDiscardRemovesEverythingItStaged(t *testing.T) {
	game := t.TempDir()
	staging, err := NewStaging(game, "run")
	if err != nil {
		t.Fatal(err)
	}
	level := write(t, filepath.Join(t.TempDir(), "warehouse.mblevel.json"), `{"schema":2}`)
	if err := staging.WriteLevel("warehouse", level, "", ""); err != nil {
		t.Fatal(err)
	}
	if err := staging.Discard(); err != nil {
		t.Fatal(err)
	}
	if ppathIsDir(staging.Dir) {
		t.Error("the staging folder survived a discard")
	}
	if ppathIsDir(filepath.Join(game, "UserData")) {
		t.Error("a discarded run wrote into the game directory")
	}
}

func TestStagingCommitRefusesAFileItDidNotStage(t *testing.T) {
	game := t.TempDir()
	staging, err := NewStaging(game, "run")
	if err != nil {
		t.Fatal(err)
	}
	level := write(t, filepath.Join(t.TempDir(), "warehouse.mblevel.json"), `{"schema":2}`)
	if err := staging.WriteLevel("warehouse", level, "", ""); err != nil {
		t.Fatal(err)
	}
	forged := filepath.Join(staging.Dir, "UserData", "Levels", "player-staged.mblevel.json")
	write(t, forged, `{"schema":2}`)
	if _, err := os.Stat(filepath.Join(game, "Megabonk.exe")); err == nil {
		t.Fatal("the fixture was expected to hold no executable")
	}
	placed, err := staging.Commit()
	if err != nil {
		t.Fatalf("commit = %v (%v)", err, placed)
	}
	if ppathIsFile(filepath.Join(game, "UserData", "Levels", "player-staged.mblevel.json")) {
		t.Errorf("a file sitting in the staged tree that this run never staged was placed: %v", placed)
	}
	if !ppathIsFile(filepath.Join(game, "UserData", "Levels", "warehouse.mblevel.json")) {
		t.Error("the level this run did stage was not placed")
	}
}

func TestStagingWritesBytesAndTracksTheTree(t *testing.T) {
	game := t.TempDir()
	staging, err := NewStaging(game, "run")
	if err != nil {
		t.Fatal(err)
	}
	if err := staging.WriteBytes("UserData/Levels/quiet.png", []byte("png bytes")); err != nil {
		t.Fatal(err)
	}
	archive := stagingZip(t, "thps.zip", [][2]string{
		{"thps/manifest.json", `{"id":"thps","name":"THPS","author":"a","version":"1","assets":["a"]}`},
		{"thps/thps", "bundle"},
	})
	if _, err := staging.InstallPack("thps", "1.2.0", archive); err != nil {
		t.Fatal(err)
	}
	if got := staging.Staged(); len(got) != 3 || !staging.Has("UserData/Levels/quiet.png") {
		t.Errorf("staged = %v", got)
	}
	placed, err := staging.Commit()
	if err != nil {
		t.Fatal(err)
	}
	want := []string{
		"UserData/LevelPacks/thps/manifest.json",
		"UserData/LevelPacks/thps/thps",
		"UserData/Levels/quiet.png",
	}
	if strings.Join(placed, ",") != strings.Join(want, ",") {
		t.Errorf("placed = %v, want %v", placed, want)
	}
	body, readErr := os.ReadFile(filepath.Join(game, "UserData", "Levels", "quiet.png"))
	if readErr != nil || string(body) != "png bytes" {
		t.Errorf("staged bytes = %q (%v)", body, readErr)
	}
}

func TestStagingWriteBytesRefusesAnUnsafeName(t *testing.T) {
	staging, err := NewStaging(t.TempDir(), "run")
	if err != nil {
		t.Fatal(err)
	}
	if err := staging.WriteBytes("../escape", []byte("no")); err == nil {
		t.Error("a name that climbs out of the tree is refused")
	}
	if err := staging.WriteBytes("UserData/../escape", []byte("no")); err == nil {
		t.Error("a name that climbs out of the tree is refused")
	}
}

func TestStagingCommitRefusesAFileRemovedAfterStaging(t *testing.T) {
	game := t.TempDir()
	staging, err := NewStaging(game, "run")
	if err != nil {
		t.Fatal(err)
	}
	level := write(t, filepath.Join(t.TempDir(), "warehouse.mblevel.json"), `{"schema":2}`)
	if err := staging.WriteLevel("warehouse", level, "", ""); err != nil {
		t.Fatal(err)
	}
	if err := os.Remove(filepath.Join(staging.Dir, "UserData", "Levels", "warehouse.mblevel.json")); err != nil {
		t.Fatal(err)
	}
	if _, err := staging.Commit(); err == nil {
		t.Error("a staged file that went missing is refused, not silently skipped")
	}
}
