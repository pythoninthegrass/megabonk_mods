package window

import (
	"strings"
	"testing"
	"time"

	native "github.com/egoist/mygo/ui"
)

func TestViewListsEveryPlannedStepWithProgress(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 520, 420)
	p.Plan([]string{"MelonLoader", "mod DLL", ".NET runtime", "levels folder"})
	p.Start(4, "install megabonk-levels")
	p.Step("MelonLoader")
	p.Step("mod DLL")
	tt.Frame()
	for _, want := range []string{"MelonLoader", "mod DLL", ".NET runtime", "levels folder", "2 of 4"} {
		if !tt.HasText(want) {
			t.Errorf("view is missing %q; texts = %v", want, tt.Texts())
		}
	}
	if tt.HasText("%") {
		t.Errorf("the percentage bar is gone; texts = %v", tt.Texts())
	}
}

// hasTextFold reports whether any text contains want, ignoring case, for tests
// about what is shown rather than how it is cased.
func hasTextFold(tt *native.Tester, want string) bool {
	want = strings.ToLower(want)
	for _, text := range tt.Texts() {
		if strings.Contains(strings.ToLower(text), want) {
			return true
		}
	}
	return false
}

func TestStatusMessageStartsWithACapital(t *testing.T) {
	for _, item := range []struct {
		message string
		ok      bool
		want    string
	}{
		{"installed", true, "Installed"},
		{"could not write the mod DLL", false, "Could not write the mod DLL"},
	} {
		p := New("Megabonk Levels installer")
		tt := native.NewTester(p.view, 520, 420)
		p.Start(1, "install megabonk-levels")
		p.Finish(item.message, item.ok)
		tt.Frame()
		if !tt.HasText(item.want) || tt.HasText(item.message) {
			t.Errorf("Finish(%q) should show %q; texts = %v", item.message, item.want, tt.Texts())
		}
	}
}

func TestHeaderStartsWithACapital(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 520, 420)
	p.Start(2, "install megabonk-levels")
	tt.Frame()
	if !tt.HasText("Install megabonk-levels") || tt.HasText("install megabonk-levels") {
		t.Errorf("texts = %v", tt.Texts())
	}
}

func TestViewListsCompletedStepsWhenNoPlanWasGiven(t *testing.T) {
	p := New("Megabonk Levels uninstaller")
	tt := native.NewTester(p.view, 520, 420)
	p.Start(2, "uninstall megabonk-levels")
	p.Step("MelonLoader")
	tt.Frame()
	if !tt.HasText("MelonLoader") {
		t.Errorf("texts = %v", tt.Texts())
	}
}

func TestCancelButtonRequestsCancel(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 520, 420)
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
	tt := native.NewTester(p.view, 520, 420)
	p.Start(1, "install megabonk-levels")
	p.Step("MelonLoader")
	p.Finish("installed", true)
	tt.Frame()
	if !hasTextFold(tt, "installed") {
		t.Errorf("the finish message should replace the step line; texts = %v", tt.Texts())
	}
	if tt.HasText("Cancel") {
		t.Errorf("a finished window has no Cancel; texts = %v", tt.Texts())
	}
	if !tt.HasText("Done") {
		t.Errorf("a finished window offers Done; texts = %v", tt.Texts())
	}
}

func TestFailureFinishIsStillReadable(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 520, 420)
	p.Start(2, "install megabonk-levels")
	p.Finish("the package does not match its manifest", false)
	tt.Frame()
	if !hasTextFold(tt, "the package does not match its manifest") {
		t.Errorf("texts = %v", tt.Texts())
	}
}

func TestFailureShowsTheMessageAndDone(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 520, 420)
	p.Plan([]string{"MelonLoader", "mod DLL"})
	p.Start(2, "install megabonk-levels")
	p.Step("MelonLoader")
	p.Finish("could not write the mod DLL", false)
	tt.Frame()
	for _, want := range []string{"could not write the mod DLL", "done"} {
		if !hasTextFold(tt, want) {
			t.Errorf("missing %q; texts = %v", want, tt.Texts())
		}
	}
}

func TestDoneDismissesAFinishedWindow(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 520, 420)
	p.Start(1, "install megabonk-levels")
	p.Finish("installed", true)
	tt.Frame()
	if err := tt.Click("Done"); err != nil {
		t.Fatalf("clicking Done: %v", err)
	}
	if !p.dismissedNow() {
		t.Error("Done did not dismiss the window")
	}
}

func TestFinishShowsTheLaunchOptionAndCopyPutsItOnTheClipboard(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 520, 420)
	p.Start(1, "install megabonk-levels")
	p.ShowLaunchOption(`WINEDLLOVERRIDES="version=n,b" %command%`)
	p.Finish("installed", true)
	tt.Frame()
	if !tt.HasText(`WINEDLLOVERRIDES="version=n,b" %command%`) {
		t.Fatalf("the launch option is missing; texts = %v", tt.Texts())
	}
	if err := tt.Click("Copy"); err != nil {
		t.Fatalf("clicking Copy: %v", err)
	}
	if got := tt.Clipboard(); got != `WINEDLLOVERRIDES="version=n,b" %command%` {
		t.Errorf("clipboard = %q", got)
	}
}

func TestDetailsRevealsTheLog(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 520, 420)
	p.Start(1, "install megabonk-levels")
	p.Log("install-file: Mods/MegabonkLevels.Mod.dll")
	tt.Frame()
	if tt.HasText("install-file: Mods/MegabonkLevels.Mod.dll") {
		t.Fatal("the log should start collapsed")
	}
	if err := tt.Click("Details"); err != nil {
		t.Fatalf("clicking Details: %v", err)
	}
	tt.Frame()
	if !tt.HasText("install-file: Mods/MegabonkLevels.Mod.dll") {
		t.Errorf("texts = %v", tt.Texts())
	}
}

func TestFailureOpensTheDetails(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 520, 420)
	p.Start(1, "install megabonk-levels")
	p.Log("copying mod DLL")
	p.Finish("boom", false)
	tt.Frame()
	if !tt.HasText("copying mod DLL") {
		t.Errorf("a failure should show the log; texts = %v", tt.Texts())
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

func TestConfirmWaitsForInstallClick(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 520, 420)
	answer := confirmInBackground(p, "Install Megabonk Levels?")
	waitForText(t, tt, "Install Megabonk Levels?")
	select {
	case <-answer:
		t.Fatal("Confirm returned before any click")
	default:
	}
	if err := tt.Click("Install"); err != nil {
		t.Fatalf("clicking Install: %v", err)
	}
	if got := <-answer; !got {
		t.Error("Install should confirm")
	}
	if p.Cancelled() {
		t.Error("confirming is not a cancel")
	}
}

func TestConfirmDeclinedByCancel(t *testing.T) {
	p := New("Megabonk Levels installer")
	tt := native.NewTester(p.view, 520, 420)
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
