// Package window shows installer progress in a MyGo native-UI window: GTK 3
// on Linux, Metal on macOS, Direct3D 11 on Windows, and never a webview, so
// no WebKitGTK is ever loaded. The app's event loop must own the process main
// goroutine, so Run pumps it on the caller while work runs on a worker.
package window

import (
	_ "embed"
	"fmt"
	"os"
	"sync"
	"sync/atomic"
	"time"

	"github.com/egoist/mygo"
	native "github.com/egoist/mygo/ui"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ui"
)

const appName = "Megabonk Levels installer"

// The checklist keeps room for this many rows of rowHeight DIPs however much
// the launch option and the details log take, so the steps never scroll away.
const (
	maxVisibleRows = 5
	rowHeight      = 28
)

// stepDelayEnv holds a Go duration that slows every step so a person or a
// script can click Cancel mid-run; unset or unparsable means no delay.
const stepDelayEnv = "MEGABONK_UI_STEP_DELAY"

//go:embed icons/check.svg
var checkSVG []byte

//go:embed icons/x.svg
var crossSVG []byte

//go:embed icons/circle.svg
var circleSVG []byte

var (
	checkIcon   = native.MustParseSVG(checkSVG)
	crossIcon   = native.MustParseSVG(crossSVG)
	pendingIcon = native.MustParseSVG(circleSVG)
)

// Progress is the installer's ui.Progress, ui.Cancellable and ui.Confirmer
// backed by one native-UI window: a checklist of steps, a collapsible details
// log, and a cancel button whose request the plan executor polls between
// actions. After the run it stays open until the person presses Done.
type Progress struct {
	title        string
	mu           sync.Mutex
	window       *mygo.Window
	label        string
	header       string
	message      string
	steps        []string
	completed    []string
	log          []string
	launchOption string
	logOpen      bool
	total        int
	done         int
	running      bool
	finished     bool
	ok           bool
	prompt       string
	asking       bool
	accepted     bool
	dismissed    bool
	answer       chan struct{}
	cancelled    atomic.Bool
	detached     atomic.Bool
}

// New returns a progress reporter whose window carries the given title.
func New(title string) *Progress {
	return &Progress{title: title, answer: make(chan struct{}, 1)}
}

// Confirm shows the prompt with Cancel and Install buttons and blocks until one is
// pressed; closing the window or Cancel declines. Nothing is changed before it
// returns true.
func (p *Progress) Confirm(prompt string) bool {
	p.mu.Lock()
	p.prompt, p.asking, p.accepted = prompt, true, false
	p.mu.Unlock()
	p.post()
	for {
		p.mu.Lock()
		accepted, asking := p.accepted, p.asking
		p.mu.Unlock()
		if accepted {
			return !p.cancelled.Load()
		}
		if !asking || p.cancelled.Load() || p.detached.Load() {
			p.mu.Lock()
			p.asking = false
			p.mu.Unlock()
			p.post()
			return false
		}
		<-p.answer
	}
}

// Plan lists the steps the run will report, so the checklist shows them all
// before any is done.
func (p *Progress) Plan(labels []string) {
	p.mu.Lock()
	p.steps = append([]string(nil), labels...)
	p.mu.Unlock()
	p.post()
}

// Log appends a line to the details log.
func (p *Progress) Log(line string) {
	p.mu.Lock()
	p.log = append(p.log, line)
	p.mu.Unlock()
	p.post()
}

// ShowLaunchOption keeps the Steam launch option for display with a Copy button.
func (p *Progress) ShowLaunchOption(option string) {
	p.mu.Lock()
	p.launchOption = option
	p.mu.Unlock()
	p.post()
}

func (p *Progress) dismissedNow() bool {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.dismissed
}

// waitDismissed blocks until Done, a window close or a quit, so the result
// stays on screen after the work returns.
func (p *Progress) waitDismissed() {
	for !p.dismissedNow() && !p.cancelled.Load() && !p.detached.Load() {
		<-p.answer
	}
}

func (p *Progress) confirming() bool {
	p.mu.Lock()
	defer p.mu.Unlock()
	return p.asking
}

// wake unblocks a pending Confirm after a click, a close or a quit.
func (p *Progress) wake() {
	select {
	case p.answer <- struct{}{}:
	default:
	}
}

// Start opens a run of total actions under the given label.
func (p *Progress) Start(total int, label string) {
	if total < 1 {
		total = 1
	}
	p.mu.Lock()
	p.total, p.done, p.label, p.header, p.message, p.running, p.finished = total, 0, label, label, "", true, false
	p.mu.Unlock()
	p.post()
}

// Step marks one action done and shows its label.
func (p *Progress) Step(label string) {
	p.mu.Lock()
	p.done++
	p.label = label
	p.completed = append(p.completed, label)
	p.log = append(p.log, label)
	p.mu.Unlock()
	p.post()
	if delay, err := time.ParseDuration(os.Getenv(stepDelayEnv)); err == nil && delay > 0 {
		time.Sleep(delay)
	}
}

// Finish closes the run with a message and disables cancel.
func (p *Progress) Finish(message string, ok bool) {
	p.mu.Lock()
	p.finished, p.message, p.ok = true, message, ok
	if !ok {
		p.logOpen = true
	}
	p.mu.Unlock()
	p.post()
}

// Cancelled reports a cancel request; the plan executor aborts between steps.
func (p *Progress) Cancelled() bool { return p.cancelled.Load() }

// post asks for a new frame without ever blocking the caller on the event loop.
func (p *Progress) post() {
	if p.detached.Load() {
		return
	}
	p.mu.Lock()
	win := p.window
	p.mu.Unlock()
	if win == nil {
		return
	}
	go func() {
		defer func() { recover() }()
		if p.detached.Load() {
			return
		}
		win.Update(func() {})
	}()
}

type viewState struct {
	header, message, prompt, launchOption string
	rows                                  []string
	log                                   []string
	logOpen                               bool
	total, done                           int
	running, finished, ok, asking         bool
	cancelled                             bool
}

func (p *Progress) snapshot() viewState {
	p.mu.Lock()
	defer p.mu.Unlock()
	rows := p.steps
	if len(rows) == 0 {
		rows = p.completed
	}
	header := p.header
	if header == "" {
		header = p.title
	}
	return viewState{
		header: header, message: p.message, prompt: p.prompt, launchOption: p.launchOption,
		rows: append([]string(nil), rows...), log: append([]string(nil), p.log...), logOpen: p.logOpen,
		total: p.total, done: p.done,
		running: p.running, finished: p.finished, ok: p.ok, asking: p.asking,
		cancelled: p.cancelled.Load(),
	}
}

func (p *Progress) view(c *native.Context) {
	v := p.snapshot()
	native.Column(c).Fill().Padding(20).Gap(12).Children(func() {
		p.heading(c, v)
		p.checklist(c, v)
		p.status(c, v)
		p.launchOptionBox(c, v)
		p.details(c, v)
		p.buttons(c, v)
	})
}

func (p *Progress) heading(c *native.Context, v viewState) {
	title := ui.Capitalize(v.header)
	if v.asking {
		title = v.prompt
	}
	native.Row(c).Gap(8).AlignItems(native.Center).Children(func() {
		native.Text(c, title).Bold().SingleLine().Grow(1)
		if v.running && !v.asking && !v.finished && v.total > 0 {
			native.Textf(c, "%d of %d", min(v.done, v.total), v.total).TextColor(c.Theme().TextMuted)
		}
		if v.finished && v.ok && v.total > 0 {
			native.Textf(c, "%d of %d", v.total, v.total).TextColor(c.Theme().TextMuted)
		}
	})
}

func (p *Progress) checklist(c *native.Context, v viewState) {
	visibleRows := min(len(v.rows), maxVisibleRows)
	native.Scroll(c).Grow(1).MinHeight(float32(visibleRows * rowHeight)).Children(func() {
		native.Column(c).Gap(6).Children(func() {
			for i, label := range v.rows {
				p.row(c, v, i, label)
			}
			if len(v.rows) == v.done && v.running && !v.finished && !v.asking {
				p.workingRow(c)
			}
		})
	})
}

func (p *Progress) row(c *native.Context, v viewState, index int, label string) {
	theme := c.Theme()
	native.Row(c).Gap(8).AlignItems(native.Center).Children(func() {
		switch {
		case v.finished && v.ok, index < v.done:
			native.Icon(c, checkIcon).TextColor(theme.Success)
			native.Text(c, label).SingleLine()
		case v.finished:
			if index == v.done {
				native.Icon(c, crossIcon).TextColor(theme.Danger)
				native.Text(c, label).SingleLine()
			} else {
				native.Icon(c, pendingIcon).TextColor(theme.TextMuted)
				native.Text(c, label).SingleLine().TextColor(theme.TextMuted)
			}
		case index == v.done && v.running && !v.asking:
			native.Spinner(c).Label(label)
			native.Text(c, label).SingleLine()
		default:
			native.Icon(c, pendingIcon).TextColor(theme.TextMuted)
			native.Text(c, label).SingleLine().TextColor(theme.TextMuted)
		}
	})
}

func (p *Progress) workingRow(c *native.Context) {
	native.Row(c).Gap(8).AlignItems(native.Center).Children(func() {
		native.Spinner(c).Label("Working")
		native.Text(c, "Working…").TextColor(c.Theme().TextMuted)
	})
}

func (p *Progress) status(c *native.Context, v viewState) {
	theme := c.Theme()
	switch {
	case v.finished && v.message != "":
		colour := theme.Success
		if !v.ok {
			colour = theme.Danger
		}
		native.Text(c, ui.Capitalize(v.message)).Wrap().TextColor(colour)
	case v.cancelled:
		native.Text(c, "Cancelling…").TextColor(theme.TextMuted)
	}
}

func (p *Progress) launchOptionBox(c *native.Context, v viewState) {
	if !v.finished || !v.ok || v.launchOption == "" {
		return
	}
	theme := c.Theme()
	native.Text(c, "Steam > Library > Megabonk > Properties, then paste this into Launch Options:").Wrap()
	native.Row(c).Gap(8).AlignItems(native.Center).Padding(8).Background(theme.Surface).Radius(theme.Radius).Children(func() {
		native.Text(c, v.launchOption).Wrap().Selectable().Grow(1)
		if native.Button(c, "Copy").Clicked() {
			c.Services().WriteClipboard(v.launchOption)
		}
	})
}

func (p *Progress) details(c *native.Context, v viewState) {
	if len(v.log) == 0 {
		return
	}
	open := v.logOpen
	native.Collapsible(c, "Details", &open, func() {
		native.Scroll(c).MaxHeight(110).Children(func() {
			native.Column(c).Gap(2).Children(func() {
				for _, line := range v.log {
					native.Text(c, line).Wrap().Selectable().TextColor(c.Theme().TextMuted)
				}
			})
		})
	})
	if open != v.logOpen {
		p.mu.Lock()
		p.logOpen = open
		p.mu.Unlock()
	}
}

func (p *Progress) buttons(c *native.Context, v viewState) {
	native.Row(c).Gap(8).Justify(native.End).Children(func() {
		if v.finished {
			if native.PrimaryButton(c, "Done").Clicked() {
				p.mu.Lock()
				p.dismissed = true
				p.mu.Unlock()
				p.wake()
			}
			return
		}
		if native.Button(c, "Cancel").Clicked() {
			p.cancelled.Store(true)
			p.wake()
		}
		if v.asking && native.PrimaryButton(c, "Install").Clicked() {
			p.mu.Lock()
			p.accepted, p.asking = true, false
			p.mu.Unlock()
			p.wake()
		}
	})
}

// Run opens the progress window, calls work on a worker goroutine, and returns
// what work returned. started is false when the app could not launch at all
// (no display, missing GTK): work never ran, and the caller should fall back
// to the unchanged headless reporter. Closing the window or pressing Cancel
// only requests the abort; work sees it through Cancelled between steps.
func Run(title string, work func(ui.Progress) int) (code int, started bool) {
	p := New(title)
	ready := make(chan struct{})
	var once sync.Once
	mygo.App.SetName(appName)
	mygo.App.OnWindowAllClosed(func() { p.detached.Store(true); p.wake() })
	mygo.App.OnQuit(func() { p.detached.Store(true); p.wake() })
	mygo.App.WhenReady(func() {
		win := mygo.NewWindow(mygo.WindowOptions{Title: title, Width: 520, Height: 520, Content: native.View(p.view)})
		win.OnClose(func(e *mygo.CloseEvent) { p.cancelled.Store(true); p.wake() })
		p.mu.Lock()
		p.window = win
		p.mu.Unlock()
		once.Do(func() { close(ready) })
	})
	result := make(chan int, 1)
	go func() {
		<-ready
		code := work(p)
		if !p.detached.Load() {
			p.waitDismissed()
		}
		if !p.detached.Load() {
			mygo.App.Quit()
		}
		result <- code
	}()
	if err := runLoop(); err != nil {
		p.detached.Store(true)
		select {
		case <-ready:
			p.cancelled.Store(true)
		default:
		}
	}
	select {
	case <-ready:
	default:
		p.detached.Store(true)
		return 0, false
	}
	return <-result, true
}

// runLoop pumps the event loop on the caller's goroutine, which must be the
// process main goroutine, and reports a failed start instead of panicking so
// the caller can fall back to plain text.
func runLoop() (err error) {
	defer func() {
		if r := recover(); r != nil {
			err = fmt.Errorf("progress window: %v", r)
		}
	}()
	return mygo.App.Run()
}
