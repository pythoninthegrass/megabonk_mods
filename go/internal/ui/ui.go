// Package ui reports progress the same way over ssh and on a desktop session.
//
// Everything the installer says can go through plain text, so nothing depends
// on a dialog being available. The desktop path is the MyGo native-UI window
// in package window, chosen by the cli driver through ShouldAttemptGUI and the
// StartWindow seam; DE-specific dialog tools (kdialog, zenity, yad) are not
// part of the Go chain — the native window is the only GUI path.
package ui

import (
	"fmt"
	"io"
	"os"
	"runtime"
	"strings"
	"unicode"
	"unicode/utf8"
)

// Progress is what the installer reports through. Start opens a run, Step marks
// one action done, Finish closes it.
type Progress interface {
	Start(total int, label string)
	Step(label string)
	Finish(message string, ok bool)
}

// Cancellable is implemented by reporters the user can abort between steps;
// plan.ApplyPlan polls it and rolls back through the recorded uninstall.
type Cancellable interface {
	Cancelled() bool
}

// Confirmer is implemented by reporters that can ask before anything changes;
// the window shows Cancel and Install buttons, text reporters never ask.
type Confirmer interface {
	Confirm(prompt string) bool
}

// Planner is implemented by reporters that list the steps of a run up front.
type Planner interface {
	Plan(labels []string)
}

// Logger is implemented by reporters that keep a details log.
type Logger interface {
	Log(line string)
}

// LaunchOptionShower is implemented by reporters that can show the Steam launch
// option the player has to paste.
type LaunchOptionShower interface {
	ShowLaunchOption(option string)
}

// NullProgress swallows everything.
type NullProgress struct{}

// Start does nothing.
func (NullProgress) Start(int, string) {}

// Step does nothing.
func (NullProgress) Step(string) {}

// Finish does nothing.
func (NullProgress) Finish(string, bool) {}

// TextProgress prints numbered plain-text lines: "3/12 copying mods".
type TextProgress struct {
	// Writer receives each line; nil writes to Out, and a nil Out is stdout.
	Writer func(line string)
	Out    io.Writer
	Total  int
	Done   int
}

// NewTextProgress returns a TextProgress writing through writer, or to stdout.
func NewTextProgress(writer func(line string)) *TextProgress {
	return &TextProgress{Writer: writer}
}

func (p *TextProgress) emit(line string) {
	if p.Writer != nil {
		p.Writer(line)
		return
	}
	out := p.Out
	if out == nil {
		out = os.Stdout
	}
	fmt.Fprintln(out, line)
}

// Start opens a run of total actions; the label is kept for a dialog only.
func (p *TextProgress) Start(total int, label string) {
	if total < 1 {
		total = 1
	}
	p.Total = total
	p.Done = 0
}

// Step marks one action done and prints its number.
func (p *TextProgress) Step(label string) {
	p.Done++
	p.emit(fmt.Sprintf("%d/%d %s", p.Done, p.Total, label))
}

// Finish prints the closing message.
func (p *TextProgress) Finish(message string, ok bool) {
	p.emit(Capitalize(message))
}

// Capitalize uppercases the first letter of s, leaving the rest as it is.
func Capitalize(s string) string {
	first, size := utf8.DecodeRuneInString(s)
	if size == 0 {
		return s
	}
	return string(unicode.ToUpper(first)) + s[size:]
}

// Environ is the process environment as a map, for the checks below.
func Environ() map[string]string {
	env := map[string]string{}
	for _, pair := range os.Environ() {
		if key, value, found := strings.Cut(pair, "="); found {
			env[key] = value
		}
	}
	return env
}

// GOOS is the platform the checks below reason about; tests replace it.
var GOOS = runtime.GOOS

// HasDisplay reports whether this session can show a window: an X11 or
// Wayland session on Linux, any session on macOS and Windows, where the
// window attempt itself is a harmless probe that falls back on failure.
func HasDisplay(env map[string]string) bool {
	switch GOOS {
	case "windows", "darwin":
		return true
	}
	return env["DISPLAY"] != "" || env["WAYLAND_DISPLAY"] != ""
}

// NonInteractive reports whether the environment forces plain text.
func NonInteractive(env map[string]string) bool {
	switch strings.ToLower(strings.TrimSpace(env["MEGABONK_NON_INTERACTIVE"])) {
	case "1", "true", "yes", "on":
		return true
	}
	return false
}

// ShouldAttemptGUI reports whether this session is one where opening the MyGo
// progress window makes sense: a desktop session, with nothing on the command line forcing plain text.
func ShouldAttemptGUI(env map[string]string, forced bool) bool {
	return !forced && !NonInteractive(env) && HasDisplay(env)
}

// WindowSkipNote explains why a desktop-looking session still got plain text
// after the progress window failed to start, or "" when text was deliberate.
func WindowSkipNote(env map[string]string) string {
	if NonInteractive(env) || !HasDisplay(env) {
		return ""
	}
	if GOOS == "linux" {
		return "the progress window could not start; progress stays on stdout — " +
			"the window needs GTK 3, e.g. 'sudo dnf install gtk3' or 'sudo apt install libgtk-3-0'; " +
			"pass --no-gui to silence this note"
	}
	return "the progress window could not start; progress stays on stdout; " +
		"pass --no-gui to silence this note"
}

// PickProgress chooses the plain-text reporter. The window path is the cli
// driver's; every fallback — including a window that could not start —
// reports in text, and --no-gui, --non-interactive or MEGABONK_NON_INTERACTIVE
// make that explicit.
func PickProgress(env map[string]string, forced bool, writer func(line string)) Progress {
	return NewTextProgress(writer)
}
