package window

import (
	"testing"
	"time"

	native "github.com/egoist/mygo/ui"
)

func TestViewShowsStepAndPercentage(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 460, 220)
	p.Start(4, "install megabonk-levels")
	p.Step("MelonLoader")
	p.Step("mod DLL")
	tt.Frame()
	for _, want := range []string{"install megabonk-levels", "2/4 mod DLL", "50%"} {
		if !tt.HasText(want) {
			t.Errorf("view is missing %q; texts = %v", want, tt.Texts())
		}
	}
}

func TestCancelButtonRequestsCancel(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 460, 220)
	p.Start(4, "install megabonk-levels")
	tt.Frame()
	if p.Cancelled() {
		t.Fatal("fresh window should not be cancelled")
	}
	if err := tt.Click("Cancel"); err != nil {
		t.Fatalf("clicking Cancel: %v", err)
	}
	if !p.Cancelled() {
		t.Error("Cancel did not request the abort")
	}
	tt.Frame()
	if !tt.HasText("Cancelling") {
		t.Errorf("after Cancel the window should say so; texts = %v", tt.Texts())
	}
}

func TestFinishShowsTheMessageAndDisablesCancel(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 460, 220)
	p.Start(1, "install megabonk-levels")
	p.Step("MelonLoader")
	p.Finish("installed", true)
	tt.Frame()
	if !tt.HasText("installed") {
		t.Errorf("the finish message should replace the step line; texts = %v", tt.Texts())
	}
	_ = tt.Click("Cancel")
	if p.Cancelled() {
		t.Error("a finished window must not take a cancel")
	}
}

func TestFailureFinishIsStillReadable(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 460, 220)
	p.Start(2, "install megabonk-levels")
	p.Finish("the package does not match its manifest", false)
	tt.Frame()
	if !tt.HasText("the package does not match its manifest") {
		t.Errorf("texts = %v", tt.Texts())
	}
}

func confirmInBackground(p *Progress, prompt string) chan bool {
	answer := make(chan bool, 1)
	go func() { answer <- p.Confirm(prompt) }()
	return answer
}

func waitForText(t *testing.T, tt *native.Tester, want string) {
	t.Helper()
	for i := 0; i < 100; i++ {
		tt.Frame()
		if tt.HasText(want) {
			return
		}
		time.Sleep(10 * time.Millisecond)
	}
	t.Fatalf("view never showed %q; texts = %v", want, tt.Texts())
}

func TestConfirmWaitsForYesClick(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 460, 220)
	answer := confirmInBackground(p, "Install Megabonk Levels?")
	waitForText(t, tt, "Install Megabonk Levels?")
	select {
	case <-answer:
		t.Fatal("Confirm returned before any click")
	default:
	}
	if err := tt.Click("Yes"); err != nil {
		t.Fatalf("clicking Yes: %v", err)
	}
	if got := <-answer; !got {
		t.Error("Yes should confirm")
	}
	if p.Cancelled() {
		t.Error("confirming is not a cancel")
	}
}

func TestConfirmDeclinedByCancel(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 460, 220)
	answer := confirmInBackground(p, "Install Megabonk Levels?")
	waitForText(t, tt, "Install Megabonk Levels?")
	if err := tt.Click("Cancel"); err != nil {
		t.Fatalf("clicking Cancel: %v", err)
	}
	if got := <-answer; got {
		t.Error("Cancel should decline")
	}
}

func TestConfirmDeclinedByClosingTheWindow(t *testing.T) {
	p := New("Megabonk Levels installer")
	answer := confirmInBackground(p, "Install Megabonk Levels?")
	for i := 0; i < 100 && !p.confirming(); i++ {
		time.Sleep(10 * time.Millisecond)
	}
	p.cancelled.Store(true)
	p.wake()
	if got := <-answer; got {
		t.Error("closing the window should decline")
	}
}

func TestStepDelayEnvSlowsEachStep(t *testing.T) {
	t.Setenv(stepDelayEnv, "40ms")
	p := New("Megabonk Levels installer")
	p.Start(2, "install megabonk-levels")
	began := time.Now()
	p.Step("MelonLoader")
	p.Step("mod DLL")
	if got := time.Since(began); got < 80*time.Millisecond {
		t.Errorf("two steps took %v, want at least 80ms", got)
	}
}

func TestStepDelayEnvIgnoresGarbage(t *testing.T) {
	t.Setenv(stepDelayEnv, "soon")
	p := New("Megabonk Levels installer")
	p.Start(1, "install megabonk-levels")
	began := time.Now()
	p.Step("MelonLoader")
	if got := time.Since(began); got > 50*time.Millisecond {
		t.Errorf("an unparsable delay must be ignored, step took %v", got)
	}
}
