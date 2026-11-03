// Package ui reports progress the same way over ssh and on a desktop session.
//
// Everything the installer says goes through plain text, so nothing depends on
// a dialog being available. The desktop dialog path (zenity, yad, or KDE's
// kdialog over D-Bus) is the companion task's; here the question is only
// whether this session could have shown one, so the run can say why it did not.
package ui

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
)

// DialogBinaries are the progress dialogs the installer would use, in order.
var DialogBinaries = []string{"zenity", "yad", "kdialog"}

// QdbusBinaries are the D-Bus tools kdialog needs.
var QdbusBinaries = []string{"qdbus-qt6", "qdbus"}

// Progress is what the installer reports through. Start opens a run, Step marks
// one action done, Finish closes it.
type Progress interface {
	Start(total int, label string)
	Step(label string)
	Finish(message string, ok bool)
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
	p.emit(message)
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

// HasDisplay reports whether the session looks like a desktop one.
func HasDisplay(env map[string]string) bool {
	return env["DISPLAY"] != "" || env["WAYLAND_DISPLAY"] != ""
}

// HasTTY probes the controlling terminal without consuming the installer's
// stdin. Tests replace it.
var HasTTY = hasTTY

func hasTTY() bool {
	handle, err := os.OpenFile("/dev/tty", ttyFlags, 0)
	if err != nil {
		return false
	}
	defer handle.Close()
	info, err := handle.Stat()
	if err != nil {
		return false
	}
	return info.Mode()&os.ModeCharDevice != 0
}

// NonInteractive reports whether the environment forces plain text.
func NonInteractive(env map[string]string) bool {
	switch strings.ToLower(strings.TrimSpace(env["MEGABONK_NON_INTERACTIVE"])) {
	case "1", "true", "yes", "on":
		return true
	}
	return false
}

// Locate is a PATH lookup; tests replace it with their own table.
type Locate func(name string) string

func defaultLocate(name string) string {
	if found, err := exec.LookPath(name); err == nil {
		return found
	}
	return ""
}

// FindDialogBinary is the first usable progress dialog, or "" when there is
// none. kdialog only counts when D-Bus and a qdbus tool are there to drive it.
func FindDialogBinary(locate Locate, env map[string]string) string {
	if locate == nil {
		locate = defaultLocate
	}
	for _, name := range DialogBinaries {
		found := locate(name)
		if found == "" {
			continue
		}
		if name == "kdialog" && !kdialogUsable(locate, env) {
			continue
		}
		return found
	}
	return ""
}

func kdialogUsable(locate Locate, env map[string]string) bool {
	if env["DBUS_SESSION_BUS_ADDRESS"] == "" {
		return false
	}
	for _, tool := range QdbusBinaries {
		if locate(tool) != "" {
			return true
		}
	}
	return false
}

// DialogSkipNote says why no dialog was chosen on what looks like a desktop, or
// "" when a dialog runs or plain text was deliberate.
func DialogSkipNote(env map[string]string, locate Locate) string {
	if NonInteractive(env) || !HasDisplay(env) || !HasTTY() {
		return ""
	}
	if FindDialogBinary(locate, env) != "" {
		return ""
	}
	return "no progress dialog found (zenity, yad, or kdialog with a qdbus tool); progress stays on stdout — " +
		"install one, e.g. 'sudo dnf install zenity' or 'sudo apt install zenity', or pass --no-gui to silence this"
}

// PickProgress chooses how to report progress. A dialog is the companion task;
// until it lands every run reports in plain text, and --no-gui,
// --non-interactive or MEGABONK_NON_INTERACTIVE make that explicit.
func PickProgress(env map[string]string, forced bool, writer func(line string)) Progress {
	return NewTextProgress(writer)
}
