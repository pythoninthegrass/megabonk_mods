package proton

import (
	"os"
	"path/filepath"
	"testing"
)

func makeExecutable(t *testing.T, path string) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte("#!/bin/sh\n"), 0o755); err != nil {
		t.Fatal(err)
	}
	return filepath.ToSlash(path)
}

func TestFindWineBinaryPrefersTheExplicitPath(t *testing.T) {
	home := t.TempDir()
	explicit := makeExecutable(t, filepath.Join(home, "mine", "wine"))
	makeExecutable(t, filepath.Join(home, "bin", "wine"))
	if got := FindWineBinary(explicit, []string{filepath.Join(home, "bin")}, nil); got != explicit {
		t.Errorf("got %q, want %q", got, explicit)
	}
}

func TestFindWineBinaryIgnoresAnExplicitPathThatIsNotThere(t *testing.T) {
	home := t.TempDir()
	onPath := makeExecutable(t, filepath.Join(home, "bin", "wine"))
	if got := FindWineBinary(filepath.ToSlash(filepath.Join(home, "gone")), []string{filepath.Join(home, "bin")}, nil); got != onPath {
		t.Errorf("got %q, want %q", got, onPath)
	}
}

func TestFindWineBinaryTriesWine64ThenWineOnPath(t *testing.T) {
	home := t.TempDir()
	wine64 := makeExecutable(t, filepath.Join(home, "bin", "wine64"))
	makeExecutable(t, filepath.Join(home, "bin", "wine"))
	if got := FindWineBinary("", []string{filepath.Join(home, "bin")}, nil); got != wine64 {
		t.Errorf("got %q, want %q", got, wine64)
	}
}

func TestFindWineBinaryFindsAWineAppUnderTheUsersApplications(t *testing.T) {
	home := t.TempDir()
	app := makeExecutable(t, filepath.Join(home, "Applications", "wine11", "Wine Devel.app", "Contents", "Resources", "wine", "bin", "wine"))
	if got := FindWineBinary("", nil, []string{filepath.Join(home, "Applications")}); got != app {
		t.Errorf("got %q, want %q", got, app)
	}
}

func TestFindWineBinaryIsEmptyWhenThereIsNoWine(t *testing.T) {
	if got := FindWineBinary("", nil, []string{t.TempDir()}); got != "" {
		t.Errorf("got %q", got)
	}
}
