package plan

import (
	"errors"
	"path/filepath"
	"testing"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/content"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/proton"
)

// recordingProgress records the reporter calls and reports a cancellation once
// the given number of steps have run, so a test can stop ApplyPlan or
// Uninstall between actions.
type recordingProgress struct {
	steps       []string
	finishes    []string
	cancelAfter int
}

func (r *recordingProgress) Start(int, string) {}
func (r *recordingProgress) Step(label string) { r.steps = append(r.steps, label) }
func (r *recordingProgress) Finish(message string, ok bool) {
	r.finishes = append(r.finishes, message)
}
func (r *recordingProgress) Cancelled() bool { return len(r.steps) >= r.cancelAfter }

func TestCancelBetweenStepsRestoresTheDirectory(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	built, err := BuildPlan(packageDir, Options{Manifest: loadManifest(t, packageDir), Game: game, Prefix: prefix, DllOverride: "auto", WineOverride: "registry"})
	if err != nil {
		t.Fatal(err)
	}
	progress := &recordingProgress{cancelAfter: 2}

	_, err = ApplyPlan(built, progress)
	if !errors.Is(err, ErrCancelled) {
		t.Fatalf("err = %v, want ErrCancelled", err)
	}
	if len(progress.steps) != 2 {
		t.Errorf("steps = %v, want exactly the two that ran", progress.steps)
	}
	for _, gone := range []string{
		filepath.Join(game, "MelonLoader"),
		filepath.Join(game, "version.dll"),
		filepath.Join(game, "Mods"),
		filepath.Join(game, "UserLibs"),
		filepath.Join(game, content.RecordName),
		proton.RuntimeTarget(prefix),
	} {
		if ppath.Exists(gone) {
			t.Errorf("%s survived the cancelled install", ppath.Name(gone))
		}
	}
	if _, ok := proton.ReadDllOverride(prefix, proton.DLLName, ""); ok {
		t.Error("the version.dll override survived the rollback")
	}
	if !ppath.Exists(filepath.Join(game, "Megabonk.exe")) {
		t.Error("the game's own files must survive")
	}
}

func TestCancelBeforeAnyActionChangesNothing(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	built, err := BuildPlan(packageDir, Options{Manifest: loadManifest(t, packageDir), Game: game, Prefix: prefix, DllOverride: "auto", WineOverride: "registry"})
	if err != nil {
		t.Fatal(err)
	}
	progress := &recordingProgress{cancelAfter: 0}

	_, err = ApplyPlan(built, progress)
	if !errors.Is(err, ErrCancelled) {
		t.Fatalf("err = %v, want ErrCancelled", err)
	}
	if ppath.Exists(filepath.Join(game, "MelonLoader")) || ppath.Exists(filepath.Join(game, content.RecordName)) {
		t.Error("a cancel before the first action must not touch the directory")
	}
}

func TestCancelAfterRepairStillRollsBackThePriorInstall(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	pkg := loadManifest(t, packageDir)
	options := Options{Manifest: pkg, Game: game, Prefix: prefix, DllOverride: "auto", WineOverride: "registry"}
	first, err := BuildPlan(packageDir, options)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(first, nil); err != nil {
		t.Fatal(err)
	}
	dll := filepath.Join(game, "Mods", "MegabonkLevels.Mod.dll")
	pdb := filepath.Join(game, "Mods", "MegabonkLevels.Mod.pdb")
	write(t, dll, "drifted")
	write(t, pdb, "drifted")
	repair, err := BuildPlan(packageDir, options)
	if err != nil {
		t.Fatal(err)
	}
	if len(repair.Actions) < 2 {
		t.Fatalf("the repair plan needs two drifted files to cancel between, got %d actions", len(repair.Actions))
	}
	progress := &recordingProgress{cancelAfter: 1}
	_, err = ApplyPlan(repair, progress)
	if !errors.Is(err, ErrCancelled) {
		t.Fatalf("err = %v, want ErrCancelled", err)
	}
	if ppath.Exists(filepath.Join(game, "MelonLoader")) || ppath.Exists(dll) || ppath.Exists(pdb) || ppath.Exists(filepath.Join(game, content.RecordName)) {
		t.Error("the cancelled repair left installer files behind")
	}
}

func TestCancelMidUninstallKeepsTheRecordForTheRerun(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	built, err := BuildPlan(packageDir, Options{Manifest: loadManifest(t, packageDir), Game: game, Prefix: prefix, DllOverride: "auto", WineOverride: "registry"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	progress := &recordingProgress{cancelAfter: 1}
	removed, err := Uninstall(game, progress)
	if !errors.Is(err, ErrCancelled) {
		t.Fatalf("err = %v, want ErrCancelled", err)
	}
	if len(removed) == 0 {
		t.Error("the first uninstall group should have run")
	}
	if content.LoadRecord(game) == nil {
		t.Error("a stopped uninstall must keep the record so a rerun can finish")
	}
	if !ppath.Exists(filepath.Join(game, "Mods", "MegabonkLevels.Mod.dll")) {
		t.Error("the cancel ran past the mod-file group")
	}
	if _, err := Uninstall(game, nil); err != nil {
		t.Fatal(err)
	}
	if content.LoadRecord(game) != nil || ppath.Exists(filepath.Join(game, "MelonLoader")) {
		t.Error("the rerun did not finish the uninstall")
	}
}
