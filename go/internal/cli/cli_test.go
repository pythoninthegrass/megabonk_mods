package cli

import (
	"archive/zip"
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"slices"
	"sort"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/content"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/gamebuild"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/modinstall"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/plan"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/proton"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/steam"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ui"
)

func write(t *testing.T, path, body string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

func sha256Body(body string) string {
	sum := sha256.Sum256([]byte(body))
	return hex.EncodeToString(sum[:])
}

func sha256File(path string) string {
	body, err := os.ReadFile(path)
	if err != nil {
		return ""
	}
	return sha256Body(string(body))
}

// writeZip writes an archive where manifest.json expects to find it and returns
// its sha256.
func writeZip(t *testing.T, path string, entries map[string]string) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	handle, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	writer := zip.NewWriter(handle)
	names := make([]string, 0, len(entries))
	for name := range entries {
		names = append(names, name)
	}
	sort.Strings(names)
	for _, name := range names {
		member, err := writer.Create(name)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := member.Write([]byte(entries[name])); err != nil {
			t.Fatal(err)
		}
	}
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}
	if err := handle.Close(); err != nil {
		t.Fatal(err)
	}
	return sha256File(path)
}

func makeGame(t *testing.T) string {
	t.Helper()
	game := filepath.Join(t.TempDir(), "Megabonk")
	if err := os.MkdirAll(filepath.Join(game, "Megabonk_Data"), 0o755); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(game, "Megabonk.exe"), "MZ")
	return game
}

type session struct {
	exit   int
	stdout *bytes.Buffer
	stderr *bytes.Buffer
}

// run drives one installer invocation headlessly: no dialog probing, no
// subprocesses, no removable-media scan.
func run(t *testing.T, argv ...string) session {
	t.Helper()
	return runAs(t, nil, nil, argv...)
}

// runOffline is run with the level site and Thunderstore pointed at local
// servers, so a whole install can be driven without a network. It hands back the
// two stubs so a test can assert on what was fetched.
func runOffline(t *testing.T, argv ...string) (session, *gallery, *store) {
	t.Helper()
	gallery, thunder := newGallery(t), newStore(t)
	got := runAs(t, func(command *Command) {
		command.Gallery = gallery.client()
		command.Thunder = thunder.client()
		command.Pins = map[string]string{fixtureLoaderVer: thunder.packDigest}
		command.ModPins = []modinstall.ModPin{{Version: fixtureModVer, SHA256: thunder.modDigest}}
	}, nil, argv...)
	return got, gallery, thunder
}

// runAs is run with the command's settings adjusted and the stubbed
// subprocess runner replaced, for a Windows-shaped invocation.
func runAs(t *testing.T, configure func(*Command), runner func([]string, time.Duration) (int, string, error), argv ...string) session {
	t.Helper()
	stdout, stderr := &bytes.Buffer{}, &bytes.Buffer{}
	command := NewCommand(stdout, stderr)
	command.GOOS = "linux"
	command.Env = map[string]string{"HOME": t.TempDir(), "MEGABONK_NON_INTERACTIVE": "1"}
	if configure != nil {
		configure(command)
	}
	command.PickProgress = func(env map[string]string, forceText bool, writer func(string)) ui.Progress {
		return ui.NewTextProgress(writer)
	}
	restoreRoots := MountRoots
	MountRoots = nil
	restoreRunner := steam.CommandRunner
	steam.CommandRunner = func(argv []string, timeout time.Duration) (int, string, error) {
		return 1, "", errors.New("stubbed")
	}
	if runner != nil {
		steam.CommandRunner = runner
	}
	t.Cleanup(func() {
		MountRoots = restoreRoots
		steam.CommandRunner = restoreRunner
	})
	return session{exit: command.Main(argv), stdout: stdout, stderr: stderr}
}

// install drives a whole run against the local site and Thunderstore and hands
// back the game folder, so a test can start from an installed game.
func install(t *testing.T) (string, *gallery, *store) {
	t.Helper()
	game := makeGame(t)
	got, gallery, thunder := runOffline(t, "--game-dir", game, "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("install exited %d: %s %s", got.exit, got.stdout, got.stderr)
	}
	return game, gallery, thunder
}

func TestInstallWritesTheWholeTree(t *testing.T) {
	game, gallery, _ := install(t)
	stdout := ""
	for _, name := range []string{
		// The level and its pictures, the pack it needs, and the mod with the
		// loader it depends on: one run places all of it.
		"UserData/Levels/" + fixtureFile,
		"UserData/Levels/thps-warehouse.png",
		"UserData/Levels/thps-warehouse.biome.png",
		"UserData/LevelPacks/" + fixturePackID + "/manifest.json",
		"BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll",
		"BepInEx/plugins/MegabonkLevels/NLayer.dll",
		"BepInEx/core/BepInEx.dll",
		"dotnet/host/fxr/6.0.36/hostfxr.dll",
		"winhttp.dll",
		content.RecordName,
	} {
		if !ppath.IsFile(filepath.Join(game, filepath.FromSlash(name))) {
			t.Errorf("%s was not installed", name)
		}
	}
	_ = stdout
	if !ppath.IsDir(filepath.Join(game, "UserData", "Levels")) {
		t.Error("UserData/Levels was not created")
	}
	// The level came through the counting route, which is what credits its author.
	if !strings.Contains(strings.Join(gallery.downloads(), " "), "/api/l/"+fixtureCode+"/download") {
		t.Errorf("the level was not fetched through the counting route: %v", gallery.downloads())
	}
}

func TestSecondRunReportsNothingToDo(t *testing.T) {
	game, _, _ := install(t)
	got, _, _ := runOffline(t, "--game-dir", game, "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	if !strings.Contains(got.stdout.String(), "nothing to do") {
		t.Errorf("stdout = %s", got.stdout)
	}
}

func TestCheckReportsWhatIsMissingThenClean(t *testing.T) {
	game := makeGame(t)
	got, _, _ := runOffline(t, "--game-dir", game, "--check", "--no-gui", fixtureCode)
	if got.exit != ExitOutOfDate {
		t.Fatalf("exit = %d, want %d\n%s", got.exit, ExitOutOfDate, got.stderr)
	}
	stdout := got.stdout.String()
	if !strings.Contains(stdout, "thing(s) are missing") {
		t.Errorf("stdout = %s", stdout)
	}
	for _, want := range []string{"fetch-level", "fetch-pack", "install-mod", "not installed"} {
		if !strings.Contains(stdout, want) {
			t.Errorf("the report should mention %q:\n%s", want, stdout)
		}
	}

	installed, _, _ := runOffline(t, "--game-dir", game, "--no-gui", fixtureCode)
	if installed.exit != ExitOK {
		t.Fatalf("install exit = %d\n%s", installed.exit, installed.stderr)
	}
	clean, _, _ := runOffline(t, "--game-dir", game, "--check", "--no-gui", fixtureCode)
	if clean.exit != ExitOK || !strings.Contains(clean.stdout.String(), "nothing to do") {
		t.Errorf("clean check = %d\n%s", clean.exit, clean.stdout)
	}
	if !strings.Contains(clean.stdout.String(), "is installed") {
		t.Errorf("a clean check should say the mod is in place:\n%s", clean.stdout)
	}
}

func TestDryRunListsEveryStepAndChangesNothing(t *testing.T) {
	game := makeGame(t)
	got, _, _ := runOffline(t, "--game-dir", game, "--dry-run", "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	stdout := got.stdout.String()
	if !strings.Contains(stdout, "would do ") {
		t.Errorf("stdout = %s", stdout)
	}
	// Every download and every install the run would carry out is listed, so the
	// player sees the whole shape of it before agreeing.
	for _, want := range []string{
		"fetch-level: download THPS: Warehouse",
		"fetch-image: download thps-warehouse.png",
		"fetch-pack: download pack " + fixturePackID,
		"install-level: " + fixtureFile,
		"install-pack: install pack " + fixturePackID,
		"install-mod:",
	} {
		if !strings.Contains(stdout, want) {
			t.Errorf("the plan should list %q:\n%s", want, stdout)
		}
	}
	if ppath.Exists(filepath.Join(game, "BepInEx")) || ppath.Exists(filepath.Join(game, "UserData")) ||
		ppath.Exists(content.RecordFilePath(game)) {
		t.Error("a dry run wrote to the game directory")
	}
}

func TestUninstallTakesItBack(t *testing.T) {
	game, _, _ := install(t)
	got := run(t, "--game-dir", game, "--uninstall", "--no-gui")
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	if !strings.Contains(got.stdout.String(), "removed ") {
		t.Errorf("stdout = %s", got.stdout)
	}
	// Everything the run placed goes, and only that: the game's own files stay.
	for _, name := range []string{
		"UserData/Levels", "UserData/LevelPacks", "BepInEx", "dotnet",
		"winhttp.dll", content.RecordName,
	} {
		if ppath.Exists(filepath.Join(game, filepath.FromSlash(name))) {
			t.Errorf("%s survived", name)
		}
	}
	if !ppath.IsFile(filepath.Join(game, gamebuild.WindowsExe)) {
		t.Error("the uninstall removed something the game owns")
	}
	again := run(t, "--game-dir", game, "--uninstall", "--no-gui")
	if again.exit != ExitOK || !strings.Contains(again.stdout.String(), "nothing to uninstall: no installer record in "+game) {
		t.Errorf("second uninstall = %d\n%s", again.exit, again.stdout)
	}
}

func TestNoInputsIsAUsageError(t *testing.T) {
	got := run(t, "--game-dir", makeGame(t))
	if got.exit != ExitUsage {
		t.Fatalf("exit = %d, want %d", got.exit, ExitUsage)
	}
	stderr := got.stderr.String()
	// The message has to teach the input, not just refuse it.
	for _, want := range []string{"nothing to install", "share code", plan.LevelFileSuffix} {
		if !strings.Contains(stderr, want) {
			t.Errorf("stderr should mention %q: %s", want, stderr)
		}
	}
}

func TestBothModFlagsIsAUsageError(t *testing.T) {
	got := run(t, "--game-dir", makeGame(t), "--mod", "--no-mod", fixtureCode)
	if got.exit != ExitUsage || !strings.Contains(got.stderr.String(), "--mod and --no-mod cannot both be given") {
		t.Errorf("exit = %d, stderr = %s", got.exit, got.stderr)
	}
}

func TestUnknownLevelIsRefused(t *testing.T) {
	game := makeGame(t)
	got, _, _ := runOffline(t, "--game-dir", game, "--no-gui", "no-such-level")
	if got.exit != ExitError {
		t.Fatalf("exit = %d, want %d", got.exit, ExitError)
	}
	// The player hears which of their words the site did not know, in the shape
	// they typed it, rather than a rewritten file name.
	if !strings.Contains(got.stderr.String(), "no-such-level") ||
		!strings.Contains(got.stderr.String(), "not a level") {
		t.Errorf("stderr = %s", got.stderr)
	}
}

func TestBadLevelFileIsRefusedBeforeAnythingChanges(t *testing.T) {
	game := makeGame(t)
	bad := filepath.Join(t.TempDir(), "broken.mblevel.json")
	write(t, bad, `{"schema": "two"}`)
	got, _, _ := runOffline(t, "--game-dir", game, "--no-gui", bad)
	if got.exit != ExitError {
		t.Fatalf("exit = %d\n%s", got.exit, got.stdout)
	}
	if !strings.Contains(got.stderr.String(), "broken.mblevel.json") {
		t.Errorf("stderr should name the file: %s", got.stderr)
	}
	if ppath.Exists(filepath.Join(game, "UserData")) || ppath.Exists(content.RecordFilePath(game)) {
		t.Error("a run that was refused still wrote to the game directory")
	}
}

func TestUnsupportedBuildExitsFour(t *testing.T) {
	native := filepath.Join(t.TempDir(), "Megabonk")
	if err := os.MkdirAll(filepath.Join(native, "Megabonk_Data"), 0o755); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(native, "Megabonk.x86_64"), "ELF")
	got := run(t, "--game-dir", native, "--no-gui", fixtureCode)
	if got.exit != ExitUnsupportedBuild {
		t.Fatalf("exit = %d, stderr = %s", got.exit, got.stderr)
	}
	if !strings.Contains(got.stderr.String(), "Linux native build") {
		t.Errorf("stderr = %s", got.stderr)
	}
}

func TestMissingGameDirExitsThree(t *testing.T) {
	missing := filepath.Join(t.TempDir(), "nope")
	got := run(t, "--game-dir", missing, "--no-gui", fixtureCode)
	if got.exit != ExitNotFound {
		t.Fatalf("exit = %d, stderr = %s", got.exit, got.stderr)
	}
	if !strings.Contains(got.stderr.String(), missing) {
		t.Errorf("the message should name the path:\n%s", got.stderr)
	}
}

func TestDiscoveryFailureNamesEveryCandidate(t *testing.T) {
	home := t.TempDir()
	got := run(t, "--home", home, "--no-gui", fixtureCode)
	if got.exit != ExitNotFound {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	stderr := got.stderr.String()
	for _, want := range []string{
		"Megabonk was not found in any Steam library.",
		"Steam clients considered:",
		".local/share/Steam",
		"does not exist",
		"Libraries searched: none — pass --library <path> to add one",
		"--game-dir <path to the folder holding Megabonk.exe>",
	} {
		if !strings.Contains(stderr, want) {
			t.Errorf("stderr should contain %q:\n%s", want, stderr)
		}
	}
}

func TestDiscoveryFindsAGameInALibrary(t *testing.T) {
	home := t.TempDir()
	library := filepath.Join(home, "library")
	game := filepath.Join(library, "steamapps", "common", steam.GameName)
	if err := os.MkdirAll(filepath.Join(game, steam.DataDir), 0o755); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(game, steam.GameExe), "MZ")
	client := filepath.Join(home, ".local", "share", "Steam")
	if err := os.MkdirAll(filepath.Join(client, "steamapps"), 0o755); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(client, "steamapps", "libraryfolders.vdf"),
		"\"libraryfolders\"\n{\n\t\"0\"\n\t{\n\t\t\"path\"\t\t\""+filepath.ToSlash(library)+"\"\n\t}\n}\n")

	got, _, _ := runOffline(t, "--home", home, "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	if !ppath.IsFile(filepath.Join(library, "steamapps", "common", steam.GameName, "BepInEx", "plugins", "MegabonkLevels", "MegabonkLevels.Mod.dll")) {
		t.Errorf("the mod was not installed into the discovered library:\n%s", got.stdout)
	}
}

func makeSteamHome(t *testing.T, libraries []string, decoy, megabonkIn string) string {
	t.Helper()
	home := t.TempDir()
	client := filepath.Join(home, ".local", "share", "Steam")
	if err := os.MkdirAll(filepath.Join(client, "steamapps"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(client, "config"), 0o755); err != nil {
		t.Fatal(err)
	}
	var body strings.Builder
	for index, library := range libraries {
		body.WriteString("\t\"" + strconv.Itoa(index) + "\"\n\t{\n\t\t\"path\"\t\t\"" + filepath.ToSlash(library) + "\"\n\t}\n")
	}
	write(t, filepath.Join(client, "steamapps", "libraryfolders.vdf"), "\"libraryfolders\"\n{\n"+body.String()+"}\n")
	for _, library := range libraries {
		if err := os.MkdirAll(filepath.Join(library, "steamapps", "common"), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if decoy != "" {
		game := filepath.Join(libraries[0], "steamapps", "common", decoy)
		if err := os.MkdirAll(filepath.Join(game, decoy+"_Data"), 0o755); err != nil {
			t.Fatal(err)
		}
		write(t, filepath.Join(game, "GameAssembly.dll"), "MZ")
		write(t, filepath.Join(game, "UnityPlayer.dll"), "MZ")
	}
	if megabonkIn != "" {
		game := filepath.Join(megabonkIn, "steamapps", "common", steam.GameName)
		if err := os.MkdirAll(filepath.Join(game, steam.DataDir), 0o755); err != nil {
			t.Fatal(err)
		}
		write(t, filepath.Join(game, steam.GameExe), "MZ")
	}
	return home
}

func makePrefix(t *testing.T, library string) string {
	t.Helper()
	prefix := filepath.Join(library, "steamapps", "compatdata", steam.AppID, "pfx")
	if err := os.MkdirAll(filepath.Join(prefix, "drive_c"), 0o755); err != nil {
		t.Fatal(err)
	}
	return filepath.ToSlash(prefix)
}

// findInstall drives discovery alone, without the flatpak probe or a media scan.
func findInstall(t *testing.T, home string, prefixChosen bool) (string, string, *bytes.Buffer, *bytes.Buffer) {
	t.Helper()
	stdout, stderr := &bytes.Buffer{}, &bytes.Buffer{}
	restoreRoots := MountRoots
	MountRoots = nil
	restoreRunner := steam.CommandRunner
	steam.CommandRunner = func(argv []string, timeout time.Duration) (int, string, error) {
		return 1, "", errors.New("stubbed")
	}
	t.Cleanup(func() {
		MountRoots = restoreRoots
		steam.CommandRunner = restoreRunner
	})
	command := NewCommand(stdout, stderr)
	command.GOOS = "linux"
	gameDir, prefix, _ := command.FindInstall(home, nil, &Reporter{Stdout: stdout, Stderr: stderr}, prefixChosen)
	return gameDir, prefix, stdout, stderr
}

func TestDiscoveryIgnoresAnUnrelatedIl2CppGameInAnEarlierLibrary(t *testing.T) {
	root := t.TempDir()
	first := filepath.Join(root, "library-0")
	second := filepath.Join(root, "library-1")
	home := makeSteamHome(t, []string{first, second}, "1000xRESIST", second)

	got, _, _ := runOffline(t, "--home", home, "--no-gui", "--wine-override", "off", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	wanted := filepath.Join(second, "steamapps", "common", steam.GameName, "BepInEx", "plugins", "MegabonkLevels", "MegabonkLevels.Mod.dll")
	if !ppath.IsFile(wanted) {
		t.Errorf("the mod was not installed into the real game:\n%s", got.stdout)
	}
	if ppath.IsDir(filepath.Join(first, "steamapps", "common", "1000xRESIST", "Mods")) {
		t.Errorf("the installer wrote into an unrelated Il2Cpp game")
	}
}

func TestNotFoundNamesTheIl2CppInstallItRejected(t *testing.T) {
	root := t.TempDir()
	first := filepath.Join(root, "library-0")
	second := filepath.Join(root, "library-1")
	home := makeSteamHome(t, []string{first, second}, "1000xRESIST", "")

	got := run(t, "--home", home, "--no-gui", fixtureCode)
	if got.exit != ExitNotFound {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	stderr := got.stderr.String()
	decoy := filepath.ToSlash(filepath.Join(first, "steamapps", "common", "1000xRESIST"))
	for _, want := range []string{decoy, "GameAssembly.dll", "Megabonk_Data", "--game-dir"} {
		if !strings.Contains(stderr, want) {
			t.Errorf("stderr should name the rejected install %q:\n%s", want, stderr)
		}
	}
}

func TestPrefixFromAnotherLibraryIsReported(t *testing.T) {
	root := t.TempDir()
	first := filepath.Join(root, "library-0")
	second := filepath.Join(root, "media", "sdcard", "SteamLibrary")
	home := makeSteamHome(t, []string{first, second}, "", second)
	active := makePrefix(t, first)

	gameDir, prefix, stdout, _ := findInstall(t, home, false)
	if want := ppath.Join(filepath.ToSlash(second), "steamapps", "common", steam.GameName); gameDir != want {
		t.Errorf("game dir = %q, want %q", gameDir, want)
	}
	if prefix != active {
		t.Errorf("prefix = %q, want the active %q", prefix, active)
	}
	out := stdout.String()
	if !strings.Contains(out, "Proton prefix: "+active) || !strings.Contains(out, "not beside the game") {
		t.Errorf("the cross-library prefix should be reported:\n%s", out)
	}
}

func TestTwoUsablePrefixesAreListedRatherThanGuessed(t *testing.T) {
	root := t.TempDir()
	first := filepath.Join(root, "library-0")
	second := filepath.Join(root, "library-1")
	third := filepath.Join(root, "media", "sdcard", "SteamLibrary")
	home := makeSteamHome(t, []string{first, second, third}, "", third)
	active := makePrefix(t, first)
	other := makePrefix(t, second)

	_, prefix, _, stderr := findInstall(t, home, false)
	if prefix != "" {
		t.Fatalf("two usable prefixes is a guess, got %q", prefix)
	}
	text := stderr.String()
	for _, want := range []string{"pass --prefix", active, other} {
		if !strings.Contains(text, want) {
			t.Errorf("stderr should list both prefixes %q:\n%s", want, text)
		}
	}
}

func TestAnExplicitPrefixSilencesTheAmbiguityWarning(t *testing.T) {
	root := t.TempDir()
	first := filepath.Join(root, "library-0")
	second := filepath.Join(root, "library-1")
	third := filepath.Join(root, "media", "sdcard", "SteamLibrary")
	home := makeSteamHome(t, []string{first, second, third}, "", third)
	makePrefix(t, first)
	chosen := makePrefix(t, second)

	got, _, _ := runOffline(t, "--home", home, "--prefix", chosen, "--dry-run", "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	if strings.Contains(got.stderr.String(), "more than one usable Proton prefix") {
		t.Errorf("--prefix was given, so the nag should be gone:\n%s", got.stderr)
	}
	if strings.Contains(got.stdout.String(), "not beside the game") {
		t.Errorf("the chosen prefix needs no commentary:\n%s", got.stdout)
	}
}

func TestJSONModeIsMachineReadable(t *testing.T) {
	game := makeGame(t)
	got, _, _ := runOffline(t, "--game-dir", game, "--json", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	var payload map[string]any
	if err := json.Unmarshal(got.stdout.Bytes(), &payload); err != nil {
		t.Fatalf("stdout is not JSON: %v\n%s", err, got.stdout)
	}
	if payload["ok"] != true || payload["dry_run"] != false {
		t.Errorf("payload = %v", payload)
	}
	// The mod comes from Thunderstore now, so the payload names what was actually
	// resolved rather than a build-time package id.
	if payload["mod_version"] != fixtureModVer || payload["bepinex_version"] != fixtureLoaderVer {
		t.Errorf("versions = %v / %v", payload["mod_version"], payload["bepinex_version"])
	}
	if taken, ok := payload["taken"].([]any); !ok || len(taken) == 0 {
		t.Errorf("taken = %v", payload["taken"])
	}
	if strings.Contains(got.stdout.String(), "installed MegabonkLevels") {
		t.Error("human text leaked into the JSON payload")
	}

	dry, _, _ := runOffline(t, "--game-dir", makeGame(t), "--json", "--dry-run", fixtureCode)
	if dry.exit != ExitOK {
		t.Fatalf("dry-run exit = %d\n%s", dry.exit, dry.stderr)
	}
	var dryPayload map[string]any
	if err := json.Unmarshal(dry.stdout.Bytes(), &dryPayload); err != nil {
		t.Fatalf("dry-run stdout is not JSON: %v", err)
	}
	if dryPayload["dry_run"] != true || dryPayload["ok"] != true {
		t.Errorf("dry-run payload = %v", dryPayload)
	}
}

func TestJSONCheckReportsDrift(t *testing.T) {
	game := makeGame(t)
	got, _, _ := runOffline(t, "--game-dir", game, "--check", "--json", fixtureCode)
	if got.exit != ExitOutOfDate {
		t.Fatalf("exit = %d", got.exit)
	}
	var payload map[string]any
	if err := json.Unmarshal(got.stdout.Bytes(), &payload); err != nil {
		t.Fatalf("stdout is not JSON: %v", err)
	}
	if payload["ok"] != false {
		t.Errorf("ok = %v", payload["ok"])
	}
	// --check answers "what is not in the game yet", so the payload lists the
	// missing steps rather than a diff against a package.
	missing, ok := payload["missing"].([]any)
	if !ok || len(missing) == 0 {
		t.Fatalf("missing = %v", payload["missing"])
	}
	entry := missing[0].(map[string]any)
	for _, key := range []string{"kind", "path", "detail"} {
		if _, found := entry[key]; !found {
			t.Errorf("drift entry has no %s: %v", key, entry)
		}
	}
}

func TestProtonRunPrintsTheLaunchOption(t *testing.T) {
	game := makeGame(t)
	prefix := filepath.Join(t.TempDir(), "steamapps", "compatdata", "3405340", "pfx")
	if err := os.MkdirAll(filepath.Join(prefix, "drive_c"), 0o755); err != nil {
		t.Fatal(err)
	}
	got, _, _ := runOffline(t, "--game-dir", game, "--prefix", prefix, "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	// The loader's winhttp proxy is picked up through a Steam launch option the
	// installer cannot write itself, so it prints the line and leaves the paste to
	// the player.
	stdout := got.stdout.String()
	for _, want := range []string{"WINEDLLOVERRIDES=", "winhttp=n,b", "%command%",
		"Steam > Library > Megabonk > Properties", "Steam rewrites its own config"} {
		if !strings.Contains(stdout, want) {
			t.Errorf("stdout should contain %q:\n%s", want, stdout)
		}
	}
	if got.stderr.String() != "" {
		t.Errorf("a plain Proton install should warn about nothing:\n%s", got.stderr)
	}
}

func TestUnusablePrefixFallsBackToTheGameDirectory(t *testing.T) {
	game := makeGame(t)
	got, _, _ := runOffline(t, "--game-dir", game,
		"--prefix", filepath.Join(t.TempDir(), "compatdata", "3405340", "pfx"), "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	stderr := got.stderr.String()
	for _, want := range []string{
		"warning: no usable Proton prefix at ",
		"the install continues beside the game",
		"pass --prefix <path to the pfx directory> to install into an existing Proton prefix",
	} {
		if !strings.Contains(stderr, want) {
			t.Errorf("stderr should contain %q:\n%s", want, stderr)
		}
	}
	if !ppath.IsFile(filepath.Join(game, content.RuntimeDirName, "host", "fxr", "6.0.36", "hostfxr.dll")) {
		t.Error("the runtime did not land beside the game")
	}
}

func TestInstalledIntoAPrefixRecordsTheOverride(t *testing.T) {
	game := makeGame(t)
	// A plain Wine prefix: only a Wine run edits the registry itself, so this is
	// the case where the record has to name the prefix uninstall will clean.
	prefix := filepath.Join(t.TempDir(), "bottles", "megabonk")
	if err := os.MkdirAll(filepath.Join(prefix, "drive_c"), 0o755); err != nil {
		t.Fatal(err)
	}
	got, _, _ := runOffline(t, "--game-dir", game, "--prefix", prefix, "--wine-override", "registry", "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	record := content.LoadRecord(game)
	// The BepInEx loader pack carries its own .NET 6 runtime and always lands it
	// beside the executable, so the record says gamedir even when the prefix was
	// edited. What the prefix has to do with the install is the override, which has
	// to name the prefix uninstall will clean.
	if record == nil || record.Runtime == nil || record.Runtime.Mode != "gamedir" {
		t.Fatalf("record = %+v", record)
	}
	if record.DllOverride == nil || !record.DllOverride.Applied {
		t.Errorf("dll_override = %+v", record.DllOverride)
	}
	if value, ok := proton.ReadDllOverride(prefix, proton.WinHTTPDLLName, ""); !ok || value != proton.WinHTTPValue {
		t.Errorf("registry override = %q, %v", value, ok)
	}
}

func TestProgressLinesAreNumbered(t *testing.T) {
	game := makeGame(t)
	got, _, _ := runOffline(t, "--game-dir", game, fixtureCode)
	lines := strings.Split(strings.TrimRight(got.stdout.String(), "\n"), "\n")
	numbered := 0
	for _, line := range lines {
		if strings.Contains(line, "/") && strings.Contains(line, " ") && (strings.HasPrefix(line, "1/") || strings.Contains(line, "/9 ")) {
			numbered++
		}
	}
	if numbered == 0 {
		t.Errorf("no numbered progress lines in:\n%s", got.stdout)
	}
}

func TestUsageErrorsExitTwo(t *testing.T) {
	if got := run(t, "--wine-override", "system"); got.exit != ExitUsage ||
		!strings.Contains(got.stderr.String(), "invalid choice: 'system'") {
		t.Errorf("bad override choice = %d\n%s", got.exit, got.stderr)
	}
	if got := run(t, "--wine-override", "maybe"); got.exit != ExitUsage ||
		!strings.Contains(got.stderr.String(), "invalid choice: 'maybe'") {
		t.Errorf("bad override = %d\n%s", got.exit, got.stderr)
	}
	if got := run(t, "--nope"); got.exit != ExitUsage ||
		!strings.Contains(got.stderr.String(), "flag provided but not defined") {
		t.Errorf("unknown flag = %d\n%s", got.exit, got.stderr)
	}
	// A level name is a word on its own, so it is never rejected as a leftover; a
	// word shaped like a flag after the levels was meant to be a flag.
	if got := run(t, "extra", "--json"); got.exit != ExitUsage ||
		!strings.Contains(got.stderr.String(), "unrecognized arguments: --json") {
		t.Errorf("flag after the levels = %d\n%s", got.exit, got.stderr)
	}
}

func TestHelpExitsZero(t *testing.T) {
	got := run(t, "--help")
	if got.exit != ExitOK {
		t.Fatalf("exit = %d", got.exit)
	}
	for _, want := range []string{"LEVEL [LEVEL ...]", "share code", "--game-dir", "--wine-override",
		"--wine-override", "--mod", "--no-mod", "--uninstall", "--check"} {
		if !strings.Contains(got.stdout.String(), want) {
			t.Errorf("help should list %q", want)
		}
	}
}

// fakeWindowProgress stands in for window.Progress in the cli tests.
type fakeWindowProgress struct {
	steps        int
	cancelAfter  int
	decline      bool
	prompts      []string
	planned      []string
	logged       []string
	finishes     []string
	launchOption string
}

func (f *fakeWindowProgress) Plan(labels []string)        { f.planned = labels }
func (f *fakeWindowProgress) Log(line string)             { f.logged = append(f.logged, line) }
func (f *fakeWindowProgress) ShowLaunchOption(opt string) { f.launchOption = opt }

func (f *fakeWindowProgress) Confirm(prompt string) bool {
	f.prompts = append(f.prompts, prompt)
	return !f.decline
}

func (f *fakeWindowProgress) Start(int, string) {}
func (f *fakeWindowProgress) Step(string)       { f.steps++ }
func (f *fakeWindowProgress) Finish(message string, ok bool) {
	f.finishes = append(f.finishes, fmt.Sprintf("%v:%s", ok, message))
}
func (f *fakeWindowProgress) Cancelled() bool { return f.cancelAfter >= 0 && f.steps >= f.cancelAfter }

// windowed builds a command whose progress window is a test driver, with the
// level site and Thunderstore served locally so a whole run can be driven offline.
func windowed(t *testing.T, driver func(title string, work func(ui.Progress) int) (int, bool)) *Command {
	t.Helper()
	stdout, stderr := &bytes.Buffer{}, &bytes.Buffer{}
	command := NewCommand(stdout, stderr)
	command.GOOS = "linux"
	command.Env = map[string]string{"HOME": t.TempDir(), "DISPLAY": ":0"}
	command.StartWindow = driver
	gallery, thunder := newGallery(t), newStore(t)
	command.Gallery = gallery.client()
	command.Thunder = thunder.client()
	command.Pins = map[string]string{fixtureLoaderVer: thunder.packDigest}
	command.ModPins = []modinstall.ModPin{{Version: fixtureModVer, SHA256: thunder.modDigest}}
	restoreRoots := MountRoots
	MountRoots = nil
	restoreGOOS := ui.GOOS
	ui.GOOS = "linux"
	restoreRunner := steam.CommandRunner
	steam.CommandRunner = func(argv []string, timeout time.Duration) (int, string, error) {
		return 1, "", errors.New("stubbed")
	}
	t.Cleanup(func() {
		MountRoots = restoreRoots
		ui.GOOS = restoreGOOS
		steam.CommandRunner = restoreRunner
	})
	return command
}

// numberedProgressLine matches the text reporter's "1/7 step" lines, not a "1/" inside a temp path.
var numberedProgressLine = regexp.MustCompile(`(?m)^\d+/\d+ `)

func TestInstallThroughTheWindowDriver(t *testing.T) {
	game := makeGame(t)
	var titles []string
	command := windowed(t, func(title string, work func(ui.Progress) int) (int, bool) {
		titles = append(titles, title)
		return work(&fakeWindowProgress{cancelAfter: -1}), true
	})
	exit := command.Main([]string{"--game-dir", game, fixtureCode})
	if exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", exit, command.Stdout, command.Stderr)
	}
	if len(titles) != 1 || titles[0] != "Megabonk Levels installer" {
		t.Errorf("titles = %v", titles)
	}
	out := command.Stdout.(*bytes.Buffer).String()
	if numberedProgressLine.MatchString(out) {
		t.Errorf("the window path must not print numbered text lines:\n%s", out)
	}
	if content.LoadRecord(game) == nil {
		t.Error("the install did not happen through the window driver")
	}
}

func TestWindowReceivesThePlanAndTheSummary(t *testing.T) {
	game := makeGame(t)
	fake := &fakeWindowProgress{cancelAfter: -1}
	command := windowed(t, func(title string, work func(ui.Progress) int) (int, bool) {
		return work(fake), true
	})
	if exit := command.Main([]string{"--game-dir", game, fixtureCode}); exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", exit, command.Stdout, command.Stderr)
	}
	if len(fake.planned) == 0 {
		t.Error("the window was never given the planned steps")
	}
	if len(fake.prompts) != 1 || fake.prompts[0] != "Install Megabonk Levels" {
		t.Errorf("prompts = %v", fake.prompts)
	}
	if !slices.ContainsFunc(fake.logged, func(line string) bool { return strings.HasPrefix(line, "installed ") }) {
		t.Errorf("the summary never reached the details log: %v", fake.logged)
	}
}

func TestWindowIsToldWhenAnInstallIsCancelled(t *testing.T) {
	game := makeGame(t)
	fake := &fakeWindowProgress{cancelAfter: 1}
	command := windowed(t, func(title string, work func(ui.Progress) int) (int, bool) {
		return work(fake), true
	})
	command.Main([]string{"--game-dir", game, fixtureCode})
	if len(fake.finishes) != 1 || !strings.HasPrefix(fake.finishes[0], "false:") || !strings.Contains(fake.finishes[0], "rolled back") {
		t.Errorf("finishes = %v", fake.finishes)
	}
}

func TestUninstallThroughTheWindowDriver(t *testing.T) {
	game := makeGame(t)
	if got, _, _ := runOffline(t, "--game-dir", game, "--no-gui", fixtureCode); got.exit != ExitOK {
		t.Fatalf("seed install exited %d: %s %s", got.exit, got.stdout, got.stderr)
	}
	var titles []string
	command := windowed(t, func(title string, work func(ui.Progress) int) (int, bool) {
		titles = append(titles, title)
		return work(&fakeWindowProgress{cancelAfter: -1}), true
	})
	exit := command.Main([]string{"--game-dir", game, "--uninstall"})
	if exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", exit, command.Stdout, command.Stderr)
	}
	if len(titles) != 1 || titles[0] != "Megabonk Levels uninstaller" {
		t.Errorf("titles = %v", titles)
	}
	if content.LoadRecord(game) != nil {
		t.Error("the uninstall did not happen through the window driver")
	}
}

func TestWindowUnavailableFallsBackToText(t *testing.T) {
	game := makeGame(t)
	attempted := 0
	command := windowed(t, func(title string, work func(ui.Progress) int) (int, bool) {
		attempted++
		return 0, false
	})
	exit := command.Main([]string{"--game-dir", game, fixtureCode})
	if exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", exit, command.Stdout, command.Stderr)
	}
	if attempted != 1 {
		t.Errorf("the window should be attempted once, got %d", attempted)
	}
	out := command.Stdout.(*bytes.Buffer).String()
	if !numberedProgressLine.MatchString(out) {
		t.Errorf("the failed window must fall back to the unchanged text reporter:\n%s", out)
	}
	note := command.Stderr.(*bytes.Buffer).String()
	if !strings.Contains(note, "GTK 3") || !strings.Contains(note, "--no-gui") {
		t.Errorf("a desktop whose window failed should be told why: %s", note)
	}
	if content.LoadRecord(game) == nil {
		t.Error("the fallback install did not happen")
	}
}

func TestNoGUINeverAttemptsTheWindow(t *testing.T) {
	game := makeGame(t)
	attempted := 0
	command := windowed(t, func(title string, work func(ui.Progress) int) (int, bool) {
		attempted++
		return work(&fakeWindowProgress{cancelAfter: -1}), true
	})
	exit := command.Main([]string{"--game-dir", game, "--no-gui", fixtureCode})
	if exit != ExitOK {
		t.Fatalf("exit = %d", exit)
	}
	if attempted != 0 {
		t.Error("--no-gui must not attempt the window")
	}
	note := command.Stderr.(*bytes.Buffer).String()
	if strings.Contains(note, "GTK 3") {
		t.Errorf("--no-gui silences the note: %s", note)
	}
}

func TestCancelledInstallThroughTheWindowReportsRollback(t *testing.T) {
	game := makeGame(t)
	command := windowed(t, func(title string, work func(ui.Progress) int) (int, bool) {
		return work(&fakeWindowProgress{cancelAfter: 2}), true
	})
	exit := command.Main([]string{"--game-dir", game, fixtureCode})
	if exit != ExitError {
		t.Fatalf("exit = %d\n%s\n%s", exit, command.Stdout, command.Stderr)
	}
	out := command.Stdout.(*bytes.Buffer).String()
	if !strings.Contains(out, "cancelled") || !strings.Contains(out, "rolled back") {
		t.Errorf("a cancelled install should say it rolled back:\n%s", out)
	}
	if content.LoadRecord(game) != nil || ppath.Exists(ppath.Join(game, "MelonLoader")) {
		t.Error("the cancelled install left installer files behind")
	}
}

func TestPlanOptionsTakeTheCommandLine(t *testing.T) {
	command := NewCommand(&bytes.Buffer{}, &bytes.Buffer{})
	command.GOOS = "linux"
	command.Env = map[string]string{"HOME": "/home/user"}
	options, err := ParseFlags([]string{
		"--game-dir", "g", "--wine-override", "registry",
		"--proton", "proton_ge", "--library", "/lib/one", "--library", "/lib/two",
		"--mod", "7N1-MVB-WKF", "https://megabonkmod.party/l/2AB-CDE-FGH", "mine.mblevel.json",
	})
	if err != nil {
		t.Fatal(err)
	}
	if len(options.Libraries) != 2 || options.Libraries[1] != "/lib/two" {
		t.Errorf("repeatable flags = %+v", options)
	}
	if len(options.Inputs) != 3 || options.Inputs[2] != "mine.mblevel.json" {
		t.Errorf("positional inputs = %v", options.Inputs)
	}
	if options.Mod != plan.ModForced {
		t.Errorf("--mod = %v", options.Mod)
	}
	built := command.planOptions(options, "/game", nil)
	if built.Game != "/game" || built.Mod != plan.ModForced || len(built.Inputs) != 3 {
		t.Errorf("plan options = %+v", built)
	}
}

// TestMountRootsHonoursTheEnvironment pins the seam tests use to keep a
// mounted library out of discovery: an empty value means "scan nothing",
// not "fall back to the defaults".
func TestMountRootsHonoursTheEnvironment(t *testing.T) {
	t.Setenv("MEGABONK_MOUNT_ROOTS", "")
	if got := defaultMountRoots(); len(got) != 0 {
		t.Errorf("an empty value means scan no mounts, got %v", got)
	}
	t.Setenv("MEGABONK_MOUNT_ROOTS", "/media,/mnt")
	if got := defaultMountRoots(); len(got) != 2 || got[0] != "/media" || got[1] != "/mnt" {
		t.Errorf("a list is taken literally: %v", got)
	}
	t.Setenv("MEGABONK_MOUNT_ROOTS", "/a,,/b")
	if got := defaultMountRoots(); len(got) != 2 {
		t.Errorf("empty entries are dropped: %v", got)
	}
	os.Unsetenv("MEGABONK_MOUNT_ROOTS")
	if got := defaultMountRoots(); len(got) != 4 {
		t.Errorf("the default scan list = %v", got)
	}
}

func TestReporterHonoursJSONMode(t *testing.T) {
	stdout, stderr := &bytes.Buffer{}, &bytes.Buffer{}
	reporter := &Reporter{AsJSON: true, Stdout: stdout, Stderr: stderr}
	reporter.Say("human")
	reporter.Warn("careful")
	reporter.Problem("broken")
	if stdout.String() != "" {
		t.Errorf("human text leaked: %s", stdout)
	}
	if stderr.String() != "warning: careful\n  - broken\n" {
		t.Errorf("stderr = %q", stderr)
	}
	if code := reporter.Fail("dead", ExitNotFound); code != ExitNotFound {
		t.Errorf("Fail = %d", code)
	}
}

func TestApplyPlanThroughTheCommandUsesTheProgressReporter(t *testing.T) {
	game := makeGame(t)
	// The plan needs a level to place; the command's progress reporter reports
	// each of its steps.
	local := filepath.Join(t.TempDir(), "home-ramp.mblevel.json")
	if err := os.WriteFile(local, []byte(`{"schema":2,"title":"Home Ramp"}`), 0o644); err != nil {
		t.Fatal(err)
	}
	_, thunder := newGallery(t), newStore(t)
	built, err := plan.BuildPlan(plan.Options{
		Game: game, Inputs: []plan.Input{{Raw: local}}, Mod: plan.ModForced,
		Thunder: thunder.client(),
		Pins:    map[string]string{fixtureLoaderVer: thunder.packDigest},
		ModPins: []modinstall.ModPin{{Version: fixtureModVer, SHA256: thunder.modDigest}},
	})
	if err != nil {
		t.Fatal(err)
	}
	lines := []string{}
	progress := ui.NewTextProgress(func(line string) { lines = append(lines, line) })
	if _, err := plan.ApplyPlan(built, progress); err != nil {
		t.Fatal(err)
	}
	if len(lines) < 5 {
		t.Fatalf("progress = %v", lines)
	}
	// Every step line is numbered "N/M label", and the run closes with the result.
	if !numberedProgressLine.MatchString(lines[0]) {
		t.Errorf("first progress line = %q", lines[0])
	}
	if lines[len(lines)-1] != "Installed" {
		t.Errorf("last progress line = %q", lines[len(lines)-1])
	}
}

func TestDecliningTheWindowConfirmationChangesNothing(t *testing.T) {
	game := makeGame(t)
	fake := &fakeWindowProgress{cancelAfter: -1, decline: true}
	command := windowed(t, func(title string, work func(ui.Progress) int) (int, bool) {
		return work(fake), true
	})
	exit := command.Main([]string{"--game-dir", game, fixtureCode})
	if exit != ExitError {
		t.Fatalf("exit = %d\n%s\n%s", exit, command.Stdout, command.Stderr)
	}
	if len(fake.prompts) != 1 || !strings.Contains(fake.prompts[0], "Install") {
		t.Errorf("prompts = %v", fake.prompts)
	}
	if content.LoadRecord(game) != nil {
		t.Error("declining must not install anything")
	}
	if !strings.Contains(command.Stdout.(*bytes.Buffer).String(), "nothing was changed") {
		t.Errorf("stdout = %s", command.Stdout)
	}
}

func TestAcceptingTheWindowConfirmationInstalls(t *testing.T) {
	game := makeGame(t)
	fake := &fakeWindowProgress{cancelAfter: -1}
	command := windowed(t, func(title string, work func(ui.Progress) int) (int, bool) {
		return work(fake), true
	})
	if exit := command.Main([]string{"--game-dir", game, fixtureCode}); exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", exit, command.Stdout, command.Stderr)
	}
	if len(fake.prompts) != 1 || content.LoadRecord(game) == nil {
		t.Errorf("prompts = %v, record = %v", fake.prompts, content.LoadRecord(game))
	}
}

// offline wraps a command configuration with the local site and Thunderstore, for
// a platform-shaped run that also has to fetch the mod.
func offline(t *testing.T, configure func(*Command)) func(*Command) {
	t.Helper()
	return func(command *Command) {
		if configure != nil {
			configure(command)
		}
		gallery, thunder := newGallery(t), newStore(t)
		command.Gallery = gallery.client()
		command.Thunder = thunder.client()
		command.Pins = map[string]string{fixtureLoaderVer: thunder.packDigest}
		command.ModPins = []modinstall.ModPin{{Version: fixtureModVer, SHA256: thunder.modDigest}}
	}
}

func windowsCommand(env map[string]string) func(*Command) {
	return func(command *Command) {
		command.GOOS = "windows"
		for key, value := range env {
			command.Env[key] = value
		}
	}
}

func registryRunner(steamPath string) func([]string, time.Duration) (int, string, error) {
	return func(argv []string, timeout time.Duration) (int, string, error) {
		if len(argv) >= 5 && argv[0] == "reg" && argv[2] == `HKCU\Software\Valve\Steam` && argv[4] == "SteamPath" && steamPath != "" {
			return 0, "\r\nHKEY_CURRENT_USER\\Software\\Valve\\Steam\r\n    SteamPath    REG_SZ    " + steamPath + "\r\n\r\n", nil
		}
		return 1, "", nil
	}
}

func TestWindowsDiscoversTheGameAndInstallsNatively(t *testing.T) {
	base := t.TempDir()
	library := filepath.Join(base, "D", "SteamLibrary")
	game := filepath.Join(library, "steamapps", "common", steam.GameName)
	if err := os.MkdirAll(filepath.Join(game, steam.DataDir), 0o755); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(game, steam.GameExe), "MZ")
	client := filepath.Join(base, "C", "Steam")
	if err := os.MkdirAll(filepath.Join(client, "steamapps"), 0o755); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(client, "steamapps", "libraryfolders.vdf"),
		"\"libraryfolders\"\n{\n\t\"0\"\n\t{\n\t\t\"path\"\t\t\""+filepath.ToSlash(library)+"\"\n\t}\n}\n")

	got := runAs(t, offline(t, windowsCommand(nil)), registryRunner(filepath.ToSlash(client)), "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	// The loader pack carries its own .NET 6 runtime, and on a native install it
	// sits in dotnet/ beside the executable where doorstop finds it with no
	// environment variable to set.
	if !ppath.IsFile(filepath.Join(game, content.RuntimeDirName, "host", "fxr", "6.0.36", "hostfxr.dll")) {
		t.Errorf("the runtime did not land beside the game:\n%s", got.stdout)
	}
	for _, unwanted := range []string{"%command%", "DOTNET_ROOT", "Launch Options", "Proton"} {
		if strings.Contains(got.stdout.String()+got.stderr.String(), unwanted) {
			t.Errorf("a native Windows run should not mention %q:\n%s\n%s", unwanted, got.stdout, got.stderr)
		}
	}
}

func TestWindowsGameDirFlagIsNativeWithoutAPrefix(t *testing.T) {
	game := makeGame(t)
	got := runAs(t, offline(t, windowsCommand(nil)), nil, "--game-dir", game, "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	if !ppath.IsFile(filepath.Join(game, content.RuntimeDirName, "host", "fxr", "6.0.36", "hostfxr.dll")) {
		t.Error("the runtime did not land under MelonLoader/Dependencies/dotnet")
	}
	if got.stderr.String() != "" {
		t.Errorf("nothing should be warned on native Windows:\n%s", got.stderr)
	}
}

func TestWindowsNotFoundSaysWhereItLookedAndWhatToDo(t *testing.T) {
	got := runAs(t, windowsCommand(map[string]string{"ProgramFiles(x86)": t.TempDir()}), registryRunner(""), "--no-gui", fixtureCode)
	if got.exit != ExitNotFound {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	stderr := got.stderr.String()
	for _, want := range []string{"--game-dir", "HKCU", "Program Files"} {
		if !strings.Contains(stderr, want) {
			t.Errorf("stderr should contain %q:\n%s", want, stderr)
		}
	}
	for _, unwanted := range []string{"flatpak", ".var", ".local/share"} {
		if strings.Contains(strings.ToLower(stderr), unwanted) {
			t.Errorf("a Windows message should not mention %q:\n%s", unwanted, stderr)
		}
	}
}

func macCommand(home string, env map[string]string) func(*Command) {
	return func(command *Command) {
		command.GOOS = "darwin"
		command.Env["HOME"] = home
		command.Env["PATH"] = ""
		for key, value := range env {
			command.Env[key] = value
		}
	}
}

// makeWineGame builds a Steam client holding Megabonk inside a Wine prefix and
// returns the prefix and the game directory.
func makeWineGame(t *testing.T, prefix string) (string, string) {
	t.Helper()
	client := filepath.Join(prefix, "drive_c", "Program Files (x86)", "Steam")
	game := filepath.Join(client, "steamapps", "common", steam.GameName)
	if err := os.MkdirAll(filepath.Join(game, steam.DataDir), 0o755); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(game, steam.GameExe), "MZ")
	write(t, filepath.Join(client, "steamapps", "libraryfolders.vdf"),
		"\"libraryfolders\"\n{\n\t\"0\"\n\t{\n\t\t\"path\"\t\t\"C:\\\\Program Files (x86)\\\\Steam\"\n\t}\n}\n")
	return prefix, game
}

func TestMacDiscoversTheWinePrefixAndInstalls(t *testing.T) {
	home := t.TempDir()
	prefix, game := makeWineGame(t, filepath.Join(home, ".local", "share", "megabonk", "wine"))
	got := runAs(t, offline(t, macCommand(home, nil)), nil, "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	if !ppath.IsFile(filepath.Join(game, content.RuntimeDirName, "host", "fxr", "6.0.36", "hostfxr.dll")) {
		t.Errorf("the runtime did not land under MelonLoader/Dependencies/dotnet:\n%s", got.stdout)
	}
	if value, found := proton.ReadDllOverride(filepath.ToSlash(prefix), proton.WinHTTPDLLName, ""); !found || value != proton.WinHTTPValue {
		t.Errorf("version.dll override = %q, found = %v", value, found)
	}
	// A Wine run edits the prefix itself, so it must not ask for a Steam launch
	// option, and must not name Proton variables it never touches.
	for _, unwanted := range []string{"%command%", "DOTNET_ROOT", "Steam > Library"} {
		if strings.Contains(got.stdout.String()+got.stderr.String(), unwanted) {
			t.Errorf("a Wine run should not mention %q:\n%s\n%s", unwanted, got.stdout, got.stderr)
		}
	}
	if !strings.Contains(got.stdout.String(), "winhttp") {
		t.Errorf("the run should say which override it set:\n%s", got.stdout)
	}
	again := runAs(t, offline(t, macCommand(home, nil)), nil, "--no-gui", fixtureCode)
	if again.exit != ExitOK || !strings.Contains(again.stdout.String(), "nothing to do") {
		t.Errorf("rerun exit = %d\n%s\n%s", again.exit, again.stdout, again.stderr)
	}
}

func TestMacPrefersPlainWineOverCrossOver(t *testing.T) {
	home := t.TempDir()
	_, plainGame := makeWineGame(t, filepath.Join(home, ".local", "share", "megabonk", "wine"))
	_, bottleGame := makeWineGame(t, filepath.Join(home, "Library", "Application Support", "CrossOver", "Bottles", "Steam"))
	got := runAs(t, offline(t, macCommand(home, nil)), nil, "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	if content.LoadRecord(filepath.ToSlash(plainGame)) == nil || content.LoadRecord(filepath.ToSlash(bottleGame)) != nil {
		t.Errorf("the install should have gone to the plain Wine prefix only")
	}
}

func TestMacCrossOverBottleIsUsedWhenThereIsNoPlainWine(t *testing.T) {
	home := t.TempDir()
	_, game := makeWineGame(t, filepath.Join(home, "Library", "Application Support", "CrossOver", "Bottles", "Steam"))
	got := runAs(t, offline(t, macCommand(home, nil)), nil, "--no-gui", fixtureCode)
	if got.exit != ExitOK || content.LoadRecord(filepath.ToSlash(game)) == nil {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
}

func TestMacGameDirInsideAPrefixDerivesThePrefix(t *testing.T) {
	base := t.TempDir()
	prefix, game := makeWineGame(t, filepath.Join(base, "elsewhere", "wine"))
	got := runAs(t, offline(t, macCommand(t.TempDir(), nil)), nil, "--game-dir", game, "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	if value, found := proton.ReadDllOverride(filepath.ToSlash(prefix), proton.WinHTTPDLLName, ""); !found || value != proton.WinHTTPValue {
		t.Errorf("version.dll override = %q, found = %v", value, found)
	}
}

func TestMacPrefixFlagFindsTheGameInAnUnusualPrefix(t *testing.T) {
	base := t.TempDir()
	prefix, game := makeWineGame(t, filepath.Join(base, "my-prefix"))
	got := runAs(t, offline(t, macCommand(t.TempDir(), nil)), nil, "--prefix", prefix, "--no-gui", fixtureCode)
	if got.exit != ExitOK || content.LoadRecord(filepath.ToSlash(game)) == nil {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
}

func TestMacGameDirOutsideAPrefixAsksForOne(t *testing.T) {
	game := makeGame(t)
	got := runAs(t, offline(t, macCommand(t.TempDir(), nil)), nil, "--game-dir", game, "--no-gui", fixtureCode)
	// The run refuses before touching anything, and says which argument it needs:
	// that is a usage problem, not a failure halfway through.
	if got.exit != ExitUsage || !strings.Contains(got.stderr.String(), "--prefix") {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	if content.LoadRecord(filepath.ToSlash(game)) != nil {
		t.Error("nothing should be installed without a prefix")
	}
}

func TestMacUninstallRestoresAVanillaGameAndClearsTheOverride(t *testing.T) {
	home := t.TempDir()
	prefix, game := makeWineGame(t, filepath.Join(home, ".local", "share", "megabonk", "wine"))
	if got := runAs(t, offline(t, macCommand(home, nil)), nil, "--no-gui", fixtureCode); got.exit != ExitOK {
		t.Fatalf("install exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	got := runAs(t, macCommand(home, nil), nil, "--uninstall", "--no-gui")
	if got.exit != ExitOK {
		t.Fatalf("uninstall exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	if _, found := proton.ReadDllOverride(filepath.ToSlash(prefix), proton.WinHTTPDLLName, ""); found {
		t.Error("the winhttp override survived uninstall")
	}
	if ppath.Exists(filepath.Join(game, "MelonLoader")) {
		t.Error("MelonLoader survived uninstall")
	}
}

func TestMacNotFoundNamesThePrefixesItTriedAndTheFlag(t *testing.T) {
	got := runAs(t, macCommand(t.TempDir(), nil), nil, "--no-gui", fixtureCode)
	if got.exit != ExitNotFound {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	stderr := got.stderr.String()
	for _, want := range []string{"--game-dir", "--prefix", "Wine"} {
		if !strings.Contains(stderr, want) {
			t.Errorf("stderr should contain %q:\n%s", want, stderr)
		}
	}
	for _, unwanted := range []string{"flatpak", "Proton"} {
		if strings.Contains(strings.ToLower(stderr), strings.ToLower(unwanted)) {
			t.Errorf("a Mac message should not mention %q:\n%s", unwanted, stderr)
		}
	}
}

// makeLibraryGame is makeGame inside a Steam library layout, with the app
// manifest recording buildID ("" leaves the manifest out).
func makeLibraryGame(t *testing.T, buildID string) string {
	t.Helper()
	library := t.TempDir()
	game := filepath.Join(library, "steamapps", "common", "Megabonk")
	if err := os.MkdirAll(filepath.Join(game, "Megabonk_Data"), 0o755); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(game, "Megabonk.exe"), "MZ")
	if buildID != "" {
		write(t, filepath.Join(library, "steamapps", "appmanifest_"+steam.AppID+".acf"),
			"\"AppState\"\n{\n\t\"appid\"\t\t\""+steam.AppID+"\"\n\t\"installdir\"\t\t\"Megabonk\"\n\t\"buildid\"\t\t\""+buildID+"\"\n}\n")
	}
	return game
}

func TestGameBuildIsNamedWithoutAWarning(t *testing.T) {
	game := makeLibraryGame(t, "21750826")
	got, _, _ := runOffline(t, "--game-dir", game, "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	// The build is named, not judged: nothing is pinned to one build any more.
	if !strings.Contains(got.stdout.String(), "game build 21750826") {
		t.Errorf("stdout = %s", got.stdout)
	}
	if strings.Contains(got.stderr.String(), "game build") {
		t.Errorf("stderr = %s", got.stderr)
	}
}

func TestUntestedGameBuildStillInstallsAndIsNamed(t *testing.T) {
	game := makeLibraryGame(t, "99999999")
	got, _, _ := runOffline(t, "--game-dir", game, "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	// An untested build still installs, and the build it installed onto is named.
	if !strings.Contains(got.stdout.String(), "game build 99999999") {
		t.Errorf("stdout = %s", got.stdout)
	}
	if strings.Contains(got.stderr.String(), "game build") {
		t.Errorf("a build nobody tested is not a warning:\n%s", got.stderr)
	}
	if !ppath.IsFile(filepath.Join(game, "BepInEx", "plugins", "MegabonkLevels", "MegabonkLevels.Mod.dll")) {
		t.Error("the mod was not installed")
	}
}

// A Steam update after the install changes the build but not the content, so a
// check still answers "is the editor there" and leaves the exit code alone.
func TestCheckIgnoresASteamUpdateAfterTheInstall(t *testing.T) {
	game := makeLibraryGame(t, "21750826")
	if got, _, _ := runOffline(t, "--game-dir", game, "--no-gui", fixtureCode); got.exit != ExitOK {
		t.Fatalf("install exit = %d\n%s", got.exit, got.stderr)
	}
	write(t, filepath.Join(filepath.Dir(filepath.Dir(game)), "appmanifest_"+steam.AppID+".acf"),
		"\"AppState\"\n{\n\t\"appid\"\t\t\""+steam.AppID+"\"\n\t\"buildid\"\t\t\"99999999\"\n}\n")
	got, _, _ := runOffline(t, "--game-dir", game, "--no-gui", "--check", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("check exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	if !strings.Contains(got.stdout.String(), "already installed") {
		t.Errorf("stdout = %s", got.stdout)
	}
}

func TestMissingAppManifestReportsTheBuildAsUnknown(t *testing.T) {
	game := makeLibraryGame(t, "")
	got, _, _ := runOffline(t, "--game-dir", game, "--no-gui", fixtureCode)
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	if !strings.Contains(got.stdout.String(), "installed game build is unknown") {
		t.Errorf("stdout = %s", got.stdout)
	}
	if strings.Contains(got.stderr.String(), "game build") {
		t.Errorf("stderr = %s", got.stderr)
	}
}

func TestInstallRecordKeepsTheInstalledGameBuild(t *testing.T) {
	game := makeLibraryGame(t, "99999999")
	if got, _, _ := runOffline(t, "--game-dir", game, "--no-gui", fixtureCode); got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	record := content.LoadRecord(game)
	if record == nil || record.InstalledGameBuildID == nil || *record.InstalledGameBuildID != "99999999" {
		t.Fatalf("record = %+v", record)
	}
	// The mod comes from Thunderstore now rather than a package pinned to one
	// build, so both fields name the build Steam has installed.
	if record.GameBuildID != "99999999" {
		t.Errorf("game_buildid = %q", record.GameBuildID)
	}
}
