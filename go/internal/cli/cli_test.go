package cli

import (
	"archive/zip"
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"testing"
	"time"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/content"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/manifest"
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

func makePackage(t *testing.T) string {
	t.Helper()
	packageDir := filepath.Join(t.TempDir(), "package")
	loader := writeZip(t, filepath.Join(packageDir, "vendor", "MelonLoader.x64.zip"), map[string]string{
		"version.dll":                                     "MZ",
		"MelonLoader/net6/MelonLoader.dll":                "MZ",
		"MelonLoader/net6/MelonLoader.runtimeconfig.json": "{}",
	})
	dotnet := writeZip(t, filepath.Join(packageDir, "vendor", "dotnet-runtime-6.0.36-win-x64.zip"), map[string]string{
		"dotnet.exe":                  "MZ",
		"host/fxr/6.0.36/hostfxr.dll": "MZ",
		"shared/Microsoft.NETCore.App/6.0.36/System.Private.CoreLib.dll": "MZ",
	})
	write(t, filepath.Join(packageDir, "mod", "MegabonkLevels.Mod.dll"), "mod dll")
	write(t, filepath.Join(packageDir, "mod", "MegabonkLevels.Mod.pdb"), "pdb")
	write(t, filepath.Join(packageDir, "mod", "NLayer.dll"), "nlayer")
	document := map[string]any{
		"schema":              manifest.PackageSchema,
		"platform":            "linux",
		"package_id":          "megabonk-levels-0.0.1-ml0.7.3-linux",
		"mod_version":         "0.0.1",
		"melonloader_version": "0.7.3",
		"game_buildid":        "21750826",
		"generated":           "2026-10-31T03:30:00Z",
		"verified_on":         []any{},
		"vendors": []any{
			map[string]any{"name": "MelonLoader.x64.zip", "url": "u", "sha256": loader, "kind": "melonloader", "version": "0.7.3"},
			map[string]any{"name": "dotnet-runtime-6.0.36-win-x64.zip", "url": "u", "sha256": dotnet, "kind": "dotnet", "version": "6.0.36"},
		},
		"files": []any{
			map[string]any{"path": "mod/MegabonkLevels.Mod.dll", "sha256": sha256Body("mod dll"), "dest": "Mods/MegabonkLevels.Mod.dll"},
			map[string]any{"path": "mod/MegabonkLevels.Mod.pdb", "sha256": sha256Body("pdb"), "dest": "Mods/MegabonkLevels.Mod.pdb"},
			map[string]any{"path": "mod/NLayer.dll", "sha256": sha256Body("nlayer"), "dest": "Mods/NLayer.dll"},
			map[string]any{"path": "mod/NLayer.dll", "sha256": sha256Body("nlayer"), "dest": "UserLibs/NLayer.dll"},
		},
	}
	body, err := json.Marshal(document)
	if err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(packageDir, "manifest.json"), string(body))
	return packageDir
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
	stdout, stderr := &bytes.Buffer{}, &bytes.Buffer{}
	command := NewCommand(stdout, stderr)
	command.Env = map[string]string{"HOME": t.TempDir(), "MEGABONK_NON_INTERACTIVE": "1"}
	command.Locate = func(string) string { return "" }
	command.PickProgress = func(env map[string]string, forceText bool, writer func(string)) ui.Progress {
		return ui.NewTextProgress(writer)
	}
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
	return session{exit: command.Main(argv), stdout: stdout, stderr: stderr}
}

func install(t *testing.T) (string, string) {
	t.Helper()
	packageDir, game := makePackage(t), makeGame(t)
	got := run(t, "--package", packageDir, "--game-dir", game, "--no-gui")
	if got.exit != ExitOK {
		t.Fatalf("install exited %d: %s %s", got.exit, got.stdout, got.stderr)
	}
	return packageDir, game
}

func TestInstallWritesTheWholeTree(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	got := run(t, "--package", packageDir, "--game-dir", game, "--no-gui")
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	stdout := got.stdout.String()
	for _, want := range []string{"installed MegabonkLevels 0.0.1 (MelonLoader 0.7.3)", "1/", "installed 20", LogHint} {
		if !strings.Contains(stdout, want) {
			t.Errorf("stdout should contain %q:\n%s", want, stdout)
		}
	}
	for _, name := range []string{
		"Mods/MegabonkLevels.Mod.dll", "Mods/MegabonkLevels.Mod.pdb", "Mods/NLayer.dll",
		"UserLibs/NLayer.dll", "MelonLoader/net6/MelonLoader.dll", "version.dll",
		"MelonLoader/" + content.VersionMarkerName, "dotnet6-win/host/fxr/6.0.36/hostfxr.dll",
		"dotnet6-win/" + proton.RuntimeMarkerName, content.RecordName,
	} {
		if !ppath.IsFile(filepath.Join(game, filepath.FromSlash(name))) {
			t.Errorf("%s was not installed", name)
		}
	}
	if !ppath.IsDir(filepath.Join(game, "UserData", "Levels")) {
		t.Error("UserData/Levels was not created")
	}
}

func TestSecondRunReportsNothingToDo(t *testing.T) {
	packageDir, game := install(t)
	got := run(t, "--package", packageDir, "--game-dir", game, "--no-gui")
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	if !strings.Contains(got.stdout.String(), "nothing to do — MegabonkLevels 0.0.1 (MelonLoader 0.7.3) is already installed") {
		t.Errorf("stdout = %s", got.stdout)
	}
	if !strings.Contains(got.stdout.String(), "already in place: "+ppath.Join(game, "Mods/NLayer.dll")) {
		t.Errorf("the idle report should list what is in place:\n%s", got.stdout)
	}
}

func TestCheckReportsDriftThenClean(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	got := run(t, "--package", packageDir, "--game-dir", game, "--check", "--no-gui")
	if got.exit != ExitOutOfDate {
		t.Fatalf("exit = %d, want %d\n%s", got.exit, ExitOutOfDate, got.stderr)
	}
	stdout := got.stdout.String()
	if !strings.Contains(stdout, "thing(s) are out of date with package megabonk-levels-0.0.1-ml0.7.3-linux") {
		t.Errorf("stdout = %s", stdout)
	}
	for _, want := range []string{"  - install-loader:", "  - install-runtime:", "  - install-file:"} {
		if !strings.Contains(stdout, want) {
			t.Errorf("drift should list %q:\n%s", want, stdout)
		}
	}

	if code := run(t, "--package", packageDir, "--game-dir", game, "--no-gui").exit; code != ExitOK {
		t.Fatalf("install exit = %d", code)
	}
	clean := run(t, "--package", packageDir, "--game-dir", game, "--check", "--no-gui")
	if clean.exit != ExitOK || !strings.Contains(clean.stdout.String(), "nothing to do — the install matches the package") {
		t.Errorf("clean check = %d\n%s", clean.exit, clean.stdout)
	}
}

func TestDryRunChangesNothing(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	got := run(t, "--package", packageDir, "--game-dir", game, "--dry-run", "--no-gui")
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	if !strings.Contains(got.stdout.String(), "would do ") {
		t.Errorf("stdout = %s", got.stdout)
	}
	if ppath.Exists(filepath.Join(game, "Mods")) || ppath.Exists(content.RecordFilePath(game)) {
		t.Error("a dry run wrote to the game directory")
	}
}

func TestUninstallTakesItBack(t *testing.T) {
	packageDir, game := install(t)
	got := run(t, "--game-dir", game, "--uninstall", "--no-gui")
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	if !strings.Contains(got.stdout.String(), "removed ") {
		t.Errorf("stdout = %s", got.stdout)
	}
	for _, name := range []string{"Mods", "MelonLoader", content.RecordName, "dotnet6-win"} {
		if ppath.Exists(filepath.Join(game, name)) {
			t.Errorf("%s survived", name)
		}
	}
	again := run(t, "--game-dir", game, "--uninstall", "--no-gui")
	if again.exit != ExitOK || !strings.Contains(again.stdout.String(), "nothing to uninstall: no installer record in "+game) {
		t.Errorf("second uninstall = %d\n%s", again.exit, again.stdout)
	}
	_ = packageDir
}

func TestMissingPackageIsAUsageError(t *testing.T) {
	got := run(t, "--game-dir", t.TempDir())
	if got.exit != ExitUsage || !strings.Contains(got.stderr.String(), "no --package") {
		t.Errorf("exit = %d, stderr = %s", got.exit, got.stderr)
	}

	got = run(t, "--package", filepath.Join(t.TempDir(), "nope"), "--game-dir", t.TempDir())
	if got.exit != ExitError || !strings.Contains(got.stderr.String(), "has no manifest.json") {
		t.Errorf("exit = %d, stderr = %s", got.exit, got.stderr)
	}
}

func TestPackageDirToleratesTheZipFolder(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	nested := filepath.Join(t.TempDir(), "download")
	if err := os.MkdirAll(nested, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.Rename(packageDir, filepath.Join(nested, "MegabonkLevels-0.0.1")); err != nil {
		t.Fatal(err)
	}
	got := run(t, "--package", nested, "--game-dir", game, "--no-gui")
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
}

func TestTamperedPackageIsRefused(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	write(t, filepath.Join(packageDir, "mod", "NLayer.dll"), "trojan")
	got := run(t, "--package", packageDir, "--game-dir", game, "--no-gui")
	if got.exit != ExitError || !strings.Contains(got.stderr.String(), "the package does not match its manifest") {
		t.Errorf("exit = %d, stderr = %s", got.exit, got.stderr)
	}
}

func TestBadLevelInputIsListed(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	bad := filepath.Join(t.TempDir(), "broken.mblevel.json")
	write(t, bad, `{"schema": "two"}`)
	got := run(t, "--package", packageDir, "--game-dir", game, "--level", bad, "--no-gui")
	if got.exit != ExitError {
		t.Fatalf("exit = %d", got.exit)
	}
	stderr := got.stderr.String()
	if !strings.Contains(stderr, "broken.mblevel.json: 'schema' must be an integer") ||
		!strings.Contains(stderr, "the level or level-pack inputs are not valid") {
		t.Errorf("stderr = %s", stderr)
	}
}

func TestUnsupportedBuildExitsFour(t *testing.T) {
	packageDir := makePackage(t)
	native := filepath.Join(t.TempDir(), "Megabonk")
	if err := os.MkdirAll(filepath.Join(native, "Megabonk_Data"), 0o755); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(native, "Megabonk.x86_64"), "ELF")
	got := run(t, "--package", packageDir, "--game-dir", native, "--no-gui")
	if got.exit != ExitUnsupportedBuild {
		t.Fatalf("exit = %d, stderr = %s", got.exit, got.stderr)
	}
	if !strings.Contains(got.stderr.String(), "Linux native build") {
		t.Errorf("stderr = %s", got.stderr)
	}
}

func TestMissingGameDirExitsThree(t *testing.T) {
	packageDir := makePackage(t)
	missing := filepath.Join(t.TempDir(), "nope")
	got := run(t, "--package", packageDir, "--game-dir", missing, "--no-gui")
	if got.exit != ExitNotFound {
		t.Fatalf("exit = %d, stderr = %s", got.exit, got.stderr)
	}
	if !strings.Contains(got.stderr.String(), missing) {
		t.Errorf("the message should name the path:\n%s", got.stderr)
	}
}

func TestDiscoveryFailureNamesEveryCandidate(t *testing.T) {
	packageDir := makePackage(t)
	home := t.TempDir()
	got := run(t, "--package", packageDir, "--home", home, "--no-gui")
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
	packageDir := makePackage(t)
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

	got := run(t, "--package", packageDir, "--home", home, "--no-gui")
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	if !ppath.IsFile(filepath.Join(library, "steamapps", "common", steam.GameName, "Mods", "MegabonkLevels.Mod.dll")) {
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
	gameDir, prefix, _ := command.FindInstall(home, nil, &Reporter{Stdout: stdout, Stderr: stderr}, prefixChosen)
	return gameDir, prefix, stdout, stderr
}

func TestDiscoveryIgnoresAnUnrelatedIl2CppGameInAnEarlierLibrary(t *testing.T) {
	packageDir := makePackage(t)
	root := t.TempDir()
	first := filepath.Join(root, "library-0")
	second := filepath.Join(root, "library-1")
	home := makeSteamHome(t, []string{first, second}, "1000xRESIST", second)

	got := run(t, "--package", packageDir, "--home", home, "--no-gui", "--wine-override", "off")
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s\n%s", got.exit, got.stdout, got.stderr)
	}
	wanted := filepath.Join(second, "steamapps", "common", steam.GameName, "Mods", "MegabonkLevels.Mod.dll")
	if !ppath.IsFile(wanted) {
		t.Errorf("the mod was not installed into the real game:\n%s", got.stdout)
	}
	if ppath.IsDir(filepath.Join(first, "steamapps", "common", "1000xRESIST", "Mods")) {
		t.Errorf("the installer wrote into an unrelated Il2Cpp game")
	}
}

func TestNotFoundNamesTheIl2CppInstallItRejected(t *testing.T) {
	packageDir := makePackage(t)
	root := t.TempDir()
	first := filepath.Join(root, "library-0")
	second := filepath.Join(root, "library-1")
	home := makeSteamHome(t, []string{first, second}, "1000xRESIST", "")

	got := run(t, "--package", packageDir, "--home", home, "--no-gui")
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

	packageDir := makePackage(t)
	got := run(t, "--package", packageDir, "--home", home, "--prefix", chosen, "--dry-run", "--no-gui")
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
	packageDir, game := makePackage(t), makeGame(t)
	got := run(t, "--package", packageDir, "--game-dir", game, "--json")
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
	if payload["package_id"] != "megabonk-levels-0.0.1-ml0.7.3-linux" {
		t.Errorf("package_id = %v", payload["package_id"])
	}
	if taken, ok := payload["taken"].([]any); !ok || len(taken) == 0 {
		t.Errorf("taken = %v", payload["taken"])
	}
	if strings.Contains(got.stdout.String(), "installed MegabonkLevels") {
		t.Error("human text leaked into the JSON payload")
	}

	dry := run(t, "--package", packageDir, "--game-dir", makeGame(t), "--json", "--dry-run")
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
	packageDir, game := makePackage(t), makeGame(t)
	got := run(t, "--package", packageDir, "--game-dir", game, "--check", "--json")
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
	drift, ok := payload["drift"].([]any)
	if !ok || len(drift) == 0 {
		t.Fatalf("drift = %v", payload["drift"])
	}
	entry := drift[0].(map[string]any)
	for _, key := range []string{"kind", "path", "detail"} {
		if _, found := entry[key]; !found {
			t.Errorf("drift entry has no %s: %v", key, entry)
		}
	}
}

func TestGamedirModePrintsTheLaunchOption(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	got := run(t, "--package", packageDir, "--game-dir", game, "--dotnet-in", "gamedir", "--no-gui")
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	stdout := got.stdout.String()
	for _, want := range []string{"DOTNET_ROOT=Z:", "%command%", "Steam > Library > Megabonk > Properties", "Steam rewrites its own config"} {
		if !strings.Contains(stdout, want) {
			t.Errorf("stdout should contain %q:\n%s", want, stdout)
		}
	}
	if got.stderr.String() != "" {
		t.Errorf("an explicit --dotnet-in gamedir is deliberate, so nothing should be warned:\n%s", got.stderr)
	}
}

func TestUnusablePrefixFallsBackToTheGameDirectory(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	got := run(t, "--package", packageDir, "--game-dir", game,
		"--prefix", filepath.Join(t.TempDir(), "compatdata", "3405340", "pfx"), "--no-gui")
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	stderr := got.stderr.String()
	for _, want := range []string{
		"warning: no usable Proton prefix at ",
		"so the .NET runtime goes beside the game",
		"pass --prefix <path to the pfx directory> to install into an existing Proton prefix",
	} {
		if !strings.Contains(stderr, want) {
			t.Errorf("stderr should contain %q:\n%s", want, stderr)
		}
	}
	if !ppath.IsFile(filepath.Join(game, "dotnet6-win", proton.RuntimeMarkerName)) {
		t.Error("the runtime did not land beside the game")
	}
}

func TestInstalledIntoAPrefixRecordsTheOverride(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	prefix := filepath.Join(t.TempDir(), "compatdata", "3405340", "pfx")
	if err := os.MkdirAll(filepath.Join(prefix, "drive_c"), 0o755); err != nil {
		t.Fatal(err)
	}
	got := run(t, "--package", packageDir, "--game-dir", game, "--prefix", prefix, "--wine-override", "registry", "--no-gui")
	if got.exit != ExitOK {
		t.Fatalf("exit = %d\n%s", got.exit, got.stderr)
	}
	record := content.LoadRecord(game)
	if record == nil || record.Runtime == nil || record.Runtime.Mode != "prefix" {
		t.Fatalf("record = %+v", record)
	}
	if record.DllOverride == nil || !record.DllOverride.Applied {
		t.Errorf("dll_override = %+v", record.DllOverride)
	}
	if value, ok := proton.ReadDllOverride(prefix, proton.DLLName, ""); !ok || value != proton.DLLValue {
		t.Errorf("registry override = %q, %v", value, ok)
	}
}

func TestProgressLinesAreNumbered(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	got := run(t, "--package", packageDir, "--game-dir", game)
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
	if got := run(t, "--dotnet-in", "system"); got.exit != ExitUsage ||
		!strings.Contains(got.stderr.String(), "invalid choice: 'system'") {
		t.Errorf("bad mode = %d\n%s", got.exit, got.stderr)
	}
	if got := run(t, "--wine-override", "maybe"); got.exit != ExitUsage ||
		!strings.Contains(got.stderr.String(), "invalid choice: 'maybe'") {
		t.Errorf("bad override = %d\n%s", got.exit, got.stderr)
	}
	if got := run(t, "--nope"); got.exit != ExitUsage ||
		!strings.Contains(got.stderr.String(), "flag provided but not defined") {
		t.Errorf("unknown flag = %d\n%s", got.exit, got.stderr)
	}
	if got := run(t, "extra", "--json"); got.exit != ExitUsage ||
		!strings.Contains(got.stderr.String(), "unrecognized arguments: extra") {
		t.Errorf("positional = %d\n%s", got.exit, got.stderr)
	}
}

func TestHelpExitsZero(t *testing.T) {
	got := run(t, "--help")
	if got.exit != ExitOK {
		t.Fatalf("exit = %d", got.exit)
	}
	for _, want := range []string{"--package", "--game-dir", "--wine-override", "--dotnet-in"} {
		if !strings.Contains(got.stdout.String(), want) {
			t.Errorf("help should list %q", want)
		}
	}
}

func TestDialogSkipNoteOnlyWithoutNoGUI(t *testing.T) {
	restore := ui.HasTTY
	ui.HasTTY = func() bool { return true }
	defer func() { ui.HasTTY = restore }()

	packageDir, game := makePackage(t), makeGame(t)
	command := NewCommand(&bytes.Buffer{}, &bytes.Buffer{})
	command.Env = map[string]string{"DISPLAY": ":0", "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus"}
	command.Locate = func(string) string { return "" }
	options, err := ParseFlags([]string{"--package", packageDir, "--game-dir", game})
	if err != nil {
		t.Fatal(err)
	}
	reporter := &Reporter{Stdout: command.Stdout, Stderr: command.Stderr}
	command.noteDialogSkip(reporter, options)
	if !strings.Contains(command.Stderr.(*bytes.Buffer).String(), "no progress dialog found") {
		t.Errorf("a desktop with no dialog should be told why progress is on stdout")
	}

	quiet, err := ParseFlags([]string{"--package", packageDir, "--game-dir", game, "--no-gui"})
	if err != nil {
		t.Fatal(err)
	}
	buffer := &bytes.Buffer{}
	command.Stderr = buffer
	command.noteDialogSkip(&Reporter{Stdout: command.Stdout, Stderr: buffer}, quiet)
	if buffer.String() != "" {
		t.Errorf("--no-gui should silence the note: %s", buffer)
	}
}

func TestPlanOptionsTakeTheCommandLine(t *testing.T) {
	command := NewCommand(&bytes.Buffer{}, &bytes.Buffer{})
	command.Env = map[string]string{"HOME": "/home/user"}
	options, err := ParseFlags([]string{
		"--package", "p", "--game-dir", "g", "--dotnet-in", "gamedir",
		"--wine-override", "registry", "--proton", "proton_ge",
		"--level", "a.mblevel.json", "--level", "b.mblevel.json", "--pack", "packs/thps",
	})
	if err != nil {
		t.Fatal(err)
	}
	if options.Libraries != nil || len(options.Levels) != 2 || options.Levels[1] != "b.mblevel.json" {
		t.Errorf("repeatable flags = %+v", options)
	}
	built := command.planOptions(options, "/game", nil)
	if built.Game != "/game" || built.RuntimeMode != "gamedir" || built.DllOverride != "registry" ||
		built.WineOverride != "registry" || built.ForcedTool != "proton_ge" ||
		built.Level != "b.mblevel.json" || built.Pack != "packs/thps" || built.Verify {
		t.Errorf("plan options = %+v", built)
	}
}

// TestMountRootsHonoursTheEnvironment pins the seam the parity harness uses to
// keep a mounted library out of discovery: an empty value means "scan nothing",
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

func TestResolvePackageDirNeedsAManifest(t *testing.T) {
	directory := t.TempDir()
	if _, found := ResolvePackageDir(directory); found {
		t.Error("an empty directory is not a package")
	}
	write(t, filepath.Join(directory, "nested", "manifest.json"), "{}")
	got, found := ResolvePackageDir(directory)
	if !found || filepath.Base(got) != "nested" {
		t.Errorf("ResolvePackageDir = %q, %v", got, found)
	}
}

func TestApplyPlanThroughTheCommandUsesTheProgressReporter(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	loaded, err := manifest.LoadManifest(ppath.Join(packageDir, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	built, err := plan.BuildPlan(packageDir, plan.Options{Manifest: loaded, Game: game, DllOverride: "auto"})
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
	if !strings.HasSuffix(lines[0], "MelonLoader") && !strings.Contains(lines[0], "/") {
		t.Errorf("first progress line = %q", lines[0])
	}
	if lines[len(lines)-1] != "installed" {
		t.Errorf("last progress line = %q", lines[len(lines)-1])
	}
}
