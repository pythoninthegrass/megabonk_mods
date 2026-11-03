// Package window shows installer progress in a MyGo native-UI window: GTK 3
// on Linux, Metal on macOS, Direct3D 11 on Windows, and never a webview, so
// no WebKitGTK is ever loaded. The app's event loop must own the process main
// goroutine, so Run pumps it on the caller while work runs on a worker.
package window

import (
	"fmt"
	"math"
	"os"
	"sync"
	"sync/atomic"
	"time"

	"github.com/egoist/mygo"
	native "github.com/egoist/mygo/ui"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ui"
)

const appName = "Megabonk Levels installer"

// stepDelayEnv holds a Go duration that slows every step so a person or a
// script can click Cancel mid-run; unset or unparsable means no delay.
const stepDelayEnv = "MEGABONK_UI_STEP_DELAY"

// Progress is the installer's ui.Progress and ui.Cancellable backed by one
// native-UI window: a step label, a percentage bar, and a cancel button whose
// request the plan executor polls between actions.
type Progress struct {
	title     string
	mu        sync.Mutex
	window    *mygo.Window
	label     string
	header    string
	message   string
	total     int
	done      int
	running   bool
	finished  bool
	ok        bool
	prompt    string
	asking    bool
	accepted  bool
	answer    chan struct{}
	cancelled atomic.Bool
	detached  atomic.Bool
}

// New returns a progress reporter whose window carries the given title.
func New(title string) *Progress {
	return &Progress{title: title, answer: make(chan struct{}, 1)}
}

// Confirm shows the prompt with Yes and Cancel buttons and blocks until one is
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

func (p *Progress) view(c *native.Context) {
	p.mu.Lock()
	label, header, message, total, done := p.label, p.header, p.message, p.total, p.done
	running, finished, ok := p.running, p.finished, p.ok
	prompt, asking := p.prompt, p.asking
	p.mu.Unlock()
	cancelled := p.cancelled.Load()

	title := header
	if title == "" {
		title = p.title
	}
	step := ""
	switch {
	case asking:
		step = prompt
	case finished && message != "":
		step = message
	case cancelled:
		step = "Cancelling…"
	case running && total > 0:
		step = fmt.Sprintf("%d/%d %s", done, total, label)
	}
	value, percent := -1.0, ""
	if running && total > 0 && !asking {
		fraction := float64(done) / float64(total)
		if fraction > 1 {
			fraction = 1
		}
		value, percent = fraction, fmt.Sprintf("%d%%", int(math.Round(fraction*100)))
	}
	if finished && ok {
		value, percent = 1, "100%"
	}

	native.Column(c).Fill().Padding(20).Gap(12).Children(func() {
		native.Text(c, title).Bold().SingleLine()
		if step != "" {
			native.Text(c, step).SingleLine()
		}
		if !asking {
			native.Row(c).Gap(8).AlignItems(native.Center).Children(func() {
				native.Progress(c, value).Grow(1)
				native.Text(c, percent)
			})
		}
		native.Row(c).Justify(native.End).Children(func() {
			if asking {
				if native.Button(c, "Yes").Clicked() {
					p.mu.Lock()
					p.accepted, p.asking = true, false
					p.mu.Unlock()
					p.wake()
				}
			}
			button := native.Button(c, "Cancel")
			if finished {
				button = button.Disabled(true)
			}
			if button.Clicked() {
				p.cancelled.Store(true)
				p.wake()
			}
		})
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
		win := mygo.NewWindow(mygo.WindowOptions{Title: title, Width: 460, Height: 220, Content: native.View(p.view)})
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
