package ui

import (
	"strings"
	"testing"
)

var desktop = map[string]string{"DISPLAY": ":0", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"}

type recorder struct{ lines []string }

func (r *recorder) write(line string) { r.lines = append(r.lines, line) }

func TestTextProgressNumbersTheSteps(t *testing.T) {
	rec := &recorder{}
	progress := NewTextProgress(rec.write)
	progress.Start(3, "install")
	progress.Step("MelonLoader")
	progress.Step("mod DLL")
	progress.Finish("done", true)
	if len(rec.lines) != 3 {
		t.Fatalf("lines = %v", rec.lines)
	}
	if rec.lines[0] != "1/3 MelonLoader" || rec.lines[1] != "2/3 mod DLL" || rec.lines[2] != "done" {
		t.Errorf("lines = %v", rec.lines)
	}
}

func TestTextProgressStartsWithNoActions(t *testing.T) {
	rec := &recorder{}
	progress := NewTextProgress(rec.write)
	progress.Start(0, "install")
	progress.Step("only")
	if len(rec.lines) != 1 || rec.lines[0] != "1/1 only" {
		t.Errorf("a zero total must not divide by zero: %v", rec.lines)
	}
}

func TestTextProgressWritesToItsWriterOnly(t *testing.T) {
	calls := 0
	progress := NewTextProgress(func(string) { calls++ })
	progress.Start(1, "x")
	progress.Step("a")
	progress.Finish("b", false)
	if calls != 2 {
		t.Errorf("calls = %d, want 2", calls)
	}
}

func TestNullProgressSwallowsEverything(t *testing.T) {
	var progress Progress = NullProgress{}
	progress.Start(2, "x")
	progress.Step("a")
	progress.Finish("b", true)
}

func TestHasDisplayReadsTheSessionEnvironment(t *testing.T) {
	restore := GOOS
	GOOS = "linux"
	defer func() { GOOS = restore }()

	cases := []struct {
		env  map[string]string
		want bool
	}{
		{map[string]string{"DISPLAY": ":0"}, true},
		{map[string]string{"WAYLAND_DISPLAY": "wayland-0"}, true},
		{map[string]string{"DISPLAY": "", "WAYLAND_DISPLAY": "", "SSH_CONNECTION": "10.0.0.1 5000 10.0.0.2 22"}, false},
		{map[string]string{}, false},
	}
	for _, item := range cases {
		if got := HasDisplay(item.env); got != item.want {
			t.Errorf("HasDisplay(%v) = %v, want %v", item.env, got, item.want)
		}
	}

	for _, platform := range []string{"darwin", "windows"} {
		GOOS = platform
		if !HasDisplay(map[string]string{}) {
			t.Errorf("on %s any session may show a window", platform)
		}
	}
}

func TestNonInteractiveEnvironmentForcesText(t *testing.T) {
	for _, value := range []string{"1", "true", "TRUE", " yes ", "on"} {
		env := map[string]string{"MEGABONK_NON_INTERACTIVE": value}
		if !NonInteractive(env) {
			t.Errorf("MEGABONK_NON_INTERACTIVE=%q should force plain text", value)
		}
	}
	for _, value := range []string{"", "0", "false", "no", "off"} {
		env := map[string]string{"MEGABONK_NON_INTERACTIVE": value}
		if NonInteractive(env) {
			t.Errorf("MEGABONK_NON_INTERACTIVE=%q should not force plain text", value)
		}
	}
}

func TestShouldAttemptGUINeedsADesktop(t *testing.T) {
	restoreGOOS := GOOS
	GOOS = "linux"
	defer func() { GOOS = restoreGOOS }()

	cases := []struct {
		env    map[string]string
		forced bool
		want   bool
	}{
		{desktop, false, true},
		{map[string]string{"WAYLAND_DISPLAY": "wayland-0"}, false, true},
		{map[string]string{}, false, false},
		{map[string]string{"DISPLAY": ":0", "SSH_CONNECTION": "10.0.0.1 5000 10.0.0.2 22"}, false, true},
		{desktop, true, false},
		{map[string]string{"DISPLAY": ":0", "MEGABONK_NON_INTERACTIVE": "1"}, false, false},
	}
	for _, item := range cases {
		if got := ShouldAttemptGUI(item.env, item.forced); got != item.want {
			t.Errorf("ShouldAttemptGUI(%v, forced=%v) = %v, want %v", item.env, item.forced, got, item.want)
		}
	}

	for _, platform := range []string{"darwin", "windows"} {
		GOOS = platform
		if !ShouldAttemptGUI(map[string]string{}, false) {
			t.Errorf("on %s a plain session must be offered the window", platform)
		}
		if ShouldAttemptGUI(map[string]string{}, true) {
			t.Errorf("on %s --no-gui must still win", platform)
		}
	}

}

func TestWindowSkipNoteOnlyWhenADesktopGotText(t *testing.T) {
	restoreGOOS := GOOS
	GOOS = "linux"
	defer func() { GOOS = restoreGOOS }()

	if note := WindowSkipNote(map[string]string{}); note != "" {
		t.Errorf("with no display there is nothing to apologise for: %q", note)
	}
	if note := WindowSkipNote(map[string]string{"DISPLAY": ":0", "MEGABONK_NON_INTERACTIVE": "1"}); note != "" {
		t.Errorf("plain text was deliberate: %q", note)
	}
	note := WindowSkipNote(map[string]string{"DISPLAY": ":0"})
	for _, want := range []string{"GTK 3", "--no-gui", "stdout", "progress window"} {
		if !strings.Contains(note, want) {
			t.Errorf("note %q should name %q", note, want)
		}
	}

	GOOS = "darwin"
	note = WindowSkipNote(map[string]string{})
	if strings.Contains(note, "GTK 3") {
		t.Errorf("macOS should not be told about GTK: %q", note)
	}
	if !strings.Contains(note, "--no-gui") || !strings.Contains(note, "stdout") {
		t.Errorf("the macOS note still explains the fallback: %q", note)
	}
}

func TestPickProgressAlwaysReportsInText(t *testing.T) {
	for _, env := range []map[string]string{desktop, {"DISPLAY": ":0"}, {}} {
		progress := PickProgress(env, false, func(string) {})
		if _, ok := progress.(*TextProgress); !ok {
			t.Errorf("PickProgress(%v) = %T, want *TextProgress", env, progress)
		}
	}
}

func TestEnvironReadsTheProcessEnvironment(t *testing.T) {
	t.Setenv("MEGABONK_UI_PROBE", "yes")
	if Environ()["MEGABONK_UI_PROBE"] != "yes" {
		t.Errorf("Environ() = %v", Environ())
	}
}
