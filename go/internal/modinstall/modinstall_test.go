package modinstall

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"sync"
	"testing"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/content"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/proton"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/thunderstore"
)

func writeFile(t *testing.T, path, body string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

func zipTo(t *testing.T, path string, entries [][2]string) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	handle, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	writer := zip.NewWriter(handle)
	for _, entry := range entries {
		member, err := writer.Create(entry[0])
		if err != nil {
			t.Fatal(err)
		}
		if _, err := member.Write([]byte(entry[1])); err != nil {
			t.Fatal(err)
		}
	}
	if err := writer.Close(); err != nil {
		t.Fatal(err)
	}
	if err := handle.Close(); err != nil {
		t.Fatal(err)
	}
	return path
}

// vanillaGameOf is the game directory a run was told to install into.
func vanillaGameOf(t *testing.T, result *Result) string {
	t.Helper()
	if result == nil {
		t.Fatal("no result to name a game directory")
	}
	return result.Game
}

func digestOf(body []byte) string {
	sum := sha256.Sum256(body)
	return hex.EncodeToString(sum[:])
}

const bepinexVersion = "9.9.9"
const modVersion = "0.2.0"

// builtinBepInExVersion is the loader pack release the installer ships a
// known-good digest for, so a build that depends on it needs no
// --bepinex-sha256 on the command line.
const builtinBepInExVersion = "6.0.788"

// stub is a local Thunderstore: the mod's metadata document and both archives.
// Nothing in these tests reaches the network.
type stub struct {
	server *httptest.Server
	// mu guards what the handler serves, which a test can change after building
	// its client.
	mu         sync.Mutex
	requests   []string
	packBody   []byte
	modBody    []byte
	packDigest string
	// modDigest is the SHA-256 the stub's mod archive carries, so a test can pin
	// the bytes it is actually being served.
	modDigest string
	// bepinexVersion is the loader pack version the served metadata depends on. A
	// test that wants the built-in pin table to apply sets it to the version the
	// installer ships a digest for.
	bepinexVersion string
	metadataFails  bool
}

func newStub(t *testing.T) *stub {
	t.Helper()
	stub := &stub{}
	packEntries := [][2]string{
		{"BepInExPack/doorstop_config.ini", "[UnityDoorstop]"},
		{"BepInExPack/winhttp.dll", "winhttp proxy"},
		{"BepInExPack/BepInEx/core/BepInEx.dll", "core"},
		{"BepInExPack/BepInEx/core/BepInEx.Unity.IL2CPP.dll", "il2cpp core"},
		{"BepInExPack/BepInEx/core/0Harmony.dll", "harmony"},
		{"BepInExPack/dotnet/coreclr.dll", "coreclr"},
		{"BepInExPack/dotnet/host/fxr/6.0.36/hostfxr.dll", "hostfxr"},
		{"BepInExPack/dotnet/shared/Microsoft.NETCore.App/6.0.36/System.Private.CoreLib.dll", "corelib"},
		{"BepInExPack/.doorstop_version", "3.5.2"},
		{"BepInExPack/changelog.txt", "6.0.788"},
	}
	stub.packBody = []byte(slurp(t, zipTo(t, filepath.Join(t.TempDir(), "pack.zip"), packEntries)))
	stub.packDigest = digestOf(stub.packBody)
	modEntries := [][2]string{
		{"manifest.json", `{"name":"MegabonkLevels","version_number":"0.2.0"}`},
		{"icon.png", "icon"},
		{"BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll", "mod dll"},
		{"BepInEx/plugins/MegabonkLevels/NLayer.dll", "nlayer"},
		{"BepInEx/plugins/MegabonkLevels/NLayer.LICENSE.txt", "license"},
	}
	stub.modBody = []byte(slurp(t, zipTo(t, filepath.Join(t.TempDir(), "mod.zip"), modEntries)))
	stub.modDigest = digestOf(stub.modBody)
	stub.bepinexVersion = bepinexVersion

	server := httptest.NewServer(http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		path := request.URL.Path
		stub.mu.Lock()
		defer stub.mu.Unlock()
		stub.requests = append(stub.requests, path)
		switch {
		case strings.HasPrefix(path, "/api/experimental/package/") && strings.HasSuffix(path, "/"):
			if stub.metadataFails {
				http.Error(writer, "gone", http.StatusNotFound)
				return
			}
			// Built per request: which loader pack version the release depends on is
			// part of what a test gets to decide, and it has to be the answer the
			// client actually receives.
			metadata, err := json.Marshal(map[string]any{
				"namespace": thunderstore.ModNamespace,
				"name":      thunderstore.ModName,
				"latest": map[string]any{
					"namespace":      thunderstore.ModNamespace,
					"name":           thunderstore.ModName,
					"version_number": modVersion,
					"full_name":      thunderstore.ModNamespace + "-" + thunderstore.ModName + "-" + modVersion,
					"dependencies":   []string{"BepInEx-BepInExPack_IL2CPP-" + stub.bepinexVersion},
					"download_url": "https://thunderstore.io/package/download/" + thunderstore.ModNamespace +
						"/" + thunderstore.ModName + "/" + modVersion + "/",
				},
			})
			if err != nil {
				http.Error(writer, err.Error(), http.StatusInternalServerError)
				return
			}
			writer.Header().Set("Content-Type", "application/json")
			_, _ = writer.Write(metadata)
		case strings.Contains(path, "BepInEx-BepInExPack_IL2CPP-"+stub.bepinexVersion+".zip"):
			writer.Header().Set("Content-Type", "application/zip")
			_, _ = writer.Write(stub.packBody)
		case strings.Contains(path, "Megabonk_Level_Editor-"+modVersion+".zip"):
			writer.Header().Set("Content-Type", "application/zip")
			_, _ = writer.Write(stub.modBody)
		default:
			http.Error(writer, "unexpected path "+path, http.StatusNotFound)
		}
	}))
	t.Cleanup(server.Close)
	stub.server = server
	return stub
}

func slurp(t *testing.T, path string) string {
	t.Helper()
	body, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return string(body)
}

func (s *stub) client() *thunderstore.Client {
	return thunderstore.NewClient(s.server.URL, s.server.URL)
}

func (s *stub) downloads() int {
	n := 0
	for _, request := range s.log() {
		if strings.HasSuffix(request, ".zip") {
			n++
		}
	}
	return n
}

// log is the request log as it stands now, so a test that swaps an archive after
// building its client sees the archives it means served.
func (s *stub) log() []string {
	s.mu.Lock()
	defer s.mu.Unlock()
	return append([]string{}, s.requests...)
}

func vanillaGame(t *testing.T) string {
	t.Helper()
	dir := filepath.Join(t.TempDir(), "Megabonk")
	writeFile(t, filepath.Join(dir, "Megabonk.exe"), "MZ")
	if err := os.MkdirAll(filepath.Join(dir, "Megabonk_Data"), 0o755); err != nil {
		t.Fatal(err)
	}
	return dir
}

func protonPrefix(t *testing.T) string {
	t.Helper()
	prefix := filepath.Join(t.TempDir(), "steamapps", "compatdata", "3405340", "pfx")
	if err := os.MkdirAll(filepath.Join(prefix, "drive_c"), 0o755); err != nil {
		t.Fatal(err)
	}
	return prefix
}

func winePrefix(t *testing.T) string {
	t.Helper()
	prefix := filepath.Join(t.TempDir(), ".wine")
	if err := os.MkdirAll(filepath.Join(prefix, "drive_c"), 0o755); err != nil {
		t.Fatal(err)
	}
	return prefix
}

func TestInstallIntoAProtonPrefixShowsTheLaunchOption(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), protonPrefix(t)
	reported := &recorder{cancelAfter: -1}
	result, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformProton,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, reported)
	if err != nil {
		t.Fatal(err)
	}
	if result.LaunchOption != proton.WinHTTPLaunchOption {
		t.Errorf("launch option = %q, want %q", result.LaunchOption, proton.WinHTTPLaunchOption)
	}
	if !reported.launchOptionShown {
		t.Error("the window was never shown the launch option to copy")
	}
	if reported.copied != proton.WinHTTPLaunchOption {
		t.Errorf("the copy button carries %q", reported.copied)
	}
	if _, found := proton.ReadDllOverride(prefix, proton.WinHTTPDLLName, ""); found {
		t.Error("a Proton prefix must not be edited behind Steam's back")
	}
	assertInstalled(t, gameDir)
}

func TestInstallIntoAWinePrefixWritesTheOverride(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	result, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if result.LaunchOption != "" {
		t.Errorf("a plain Wine prefix needs no Steam launch option, got %q", result.LaunchOption)
	}
	if !result.OverrideApplied || result.OverrideVia == "" {
		t.Errorf("override = %+v", result)
	}
	value, found := proton.ReadDllOverride(prefix, proton.WinHTTPDLLName, "")
	if !found || value != proton.WinHTTPValue {
		t.Errorf("winhttp = %q, found = %v", value, found)
	}
	assertInstalled(t, gameDir)
	record := content.LoadRecord(gameDir)
	if record == nil || record.DllOverride == nil || !record.DllOverride.Applied ||
		record.DllOverride.Prefix == nil || *record.DllOverride.Prefix != ppath.Normalize(prefix) {
		t.Errorf("record dll_override = %+v", record)
	}
}

func TestInstallIntoACrossOverBottleWritesTheOverride(t *testing.T) {
	stub := newStub(t)
	gameDir := filepath.Join(t.TempDir(), "CrossOver Bots", "Megabonk", "drive_c",
		"Program Files (x86)", "Steam", "steamapps", "common", "Megabonk")
	writeFile(t, filepath.Join(gameDir, "Megabonk.exe"), "MZ")
	if err := os.MkdirAll(filepath.Join(gameDir, "Megabonk_Data"), 0o755); err != nil {
		t.Fatal(err)
	}
	prefix := bottleOf(t, gameDir)
	if _, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil); err != nil {
		t.Fatal(err)
	}
	if !proton.WinHTTPOverrideApplied(prefix) {
		t.Errorf("the CrossOver prefix %s has no winhttp override", prefix)
	}
	assertInstalled(t, gameDir)
}

func bottleOf(t *testing.T, gameDir string) string {
	t.Helper()
	normal := filepath.ToSlash(gameDir)
	index := strings.Index(normal, "/drive_c/")
	if index <= 0 {
		t.Fatal("not a prefix path: " + normal)
	}
	return normal[:index]
}

func TestNativeWindowsInstallSetsNoOverride(t *testing.T) {
	stub := newStub(t)
	gameDir := vanillaGame(t)
	result, err := Install(stub.client(), Options{
		Game: gameDir, Platform: PlatformNative,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if result.LaunchOption != "" || result.OverrideApplied {
		t.Errorf("a native Windows install should set nothing, got %+v", result)
	}
	record := content.LoadRecord(gameDir)
	if record == nil {
		t.Fatal("no record was written")
	}
	if record.DllOverride != nil {
		t.Errorf("the record carries a dll override for a native install: %+v", record.DllOverride)
	}
	assertInstalled(t, gameDir)
}

func TestInstallWithoutAPrefixRefuses(t *testing.T) {
	stub := newStub(t)
	gameDir := vanillaGame(t)
	_, err := Install(stub.client(), Options{
		Game: gameDir, Platform: PlatformProton,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err == nil || !strings.Contains(err.Error(), "prefix") {
		t.Errorf("no usable prefix = %v", err)
	}
	if ppath.IsDir(filepath.Join(gameDir, "BepInEx")) {
		t.Error("a refused install still wrote the loader")
	}
}

func TestInstallRefusesAnUnpinnedArchive(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	_, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
	}, nil)
	if err == nil || !strings.Contains(err.Error(), "SHA-256") {
		t.Errorf("an unpinned loader pack = %v", err)
	}
	if ppath.IsDir(filepath.Join(gameDir, "BepInEx")) {
		t.Error("an unverified archive still installed")
	}
	if stub.downloads() != 0 {
		t.Errorf("an unpinned pack was still downloaded: %v", stub.log())
	}
}

func TestInstallRefusesATamperedArchive(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	_, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: digestOf([]byte("some other archive"))},
	}, nil)
	if err == nil || !strings.Contains(strings.ToLower(err.Error()), "checksum") {
		t.Errorf("a tampered loader pack = %v", err)
	}
	if ppath.IsDir(filepath.Join(gameDir, "BepInEx")) {
		t.Error("an unverified archive still installed")
	}
}

func TestInstallIsANoopWhenTheModIsAlreadyInstalled(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	if _, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil); err != nil {
		t.Fatal(err)
	}
	before := len(stub.log())
	result, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !result.Noop {
		t.Errorf("a second install planned %v", result.Placed)
	}
	if len(stub.log()) != before {
		t.Errorf("a no-op install asked Thunderstore for %d more things", len(stub.log())-before)
	}
}

func TestInstallParksAndRestoresTheMelonLoaderProxy(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	writeFile(t, filepath.Join(gameDir, "version.dll"), "melon loader proxy")
	if err := os.MkdirAll(filepath.Join(gameDir, "MelonLoader"), 0o755); err != nil {
		t.Fatal(err)
	}
	result, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !result.ProxyParked {
		t.Error("the MelonLoader proxy was left loaded")
	}
	if ppath.Exists(filepath.Join(gameDir, "version.dll")) {
		t.Error("both loaders were left active")
	}
	record := content.LoadRecord(gameDir)
	if record == nil || record.Loader == nil || !record.Loader.ProxyParked {
		t.Fatalf("record loader = %+v", record)
	}
	if _, err := Uninstall(gameDir, nil); err != nil {
		t.Fatal(err)
	}
	body, err := os.ReadFile(filepath.Join(gameDir, "version.dll"))
	if err != nil {
		t.Fatalf("version.dll was not restored: %v", err)
	}
	if string(body) != "melon loader proxy" {
		t.Errorf("version.dll = %q", body)
	}
	if ppath.Exists(filepath.Join(gameDir, "version.dll.bak")) {
		t.Error("the backup stayed behind")
	}
	if proton.WinHTTPOverrideApplied(prefix) {
		t.Error("the winhttp override survived the uninstall")
	}
}

func TestUninstallTakesBackTheWholeModInstall(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	if _, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil); err != nil {
		t.Fatal(err)
	}
	playerLevel := filepath.Join(gameDir, "UserData", "Levels", "mine.mblevel.json")
	writeFile(t, playerLevel, `{"schema":2}`)
	other := filepath.Join(gameDir, "BepInEx", "plugins", "Other", "Other.dll")
	writeFile(t, other, "other mod")

	removed, err := Uninstall(gameDir, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(removed) == 0 {
		t.Fatal("nothing was removed")
	}
	for _, name := range []string{"dotnet", "changelog.txt", ".doorstop_version",
		"winhttp.dll", "doorstop_config.ini", "BepInEx/core", "BepInEx/plugins/MegabonkLevels"} {
		if ppath.Exists(filepath.Join(gameDir, filepath.FromSlash(name))) {
			t.Errorf("%s survived", name)
		}
	}
	if !ppath.IsFile(playerLevel) {
		t.Error("the player's own level was removed")
	}
	if !ppath.IsFile(other) {
		t.Error("another mod's files were removed")
	}
	if content.ModInstalled(gameDir) {
		t.Error("the mod still detects as installed")
	}
	if proton.WinHTTPOverrideApplied(prefix) {
		t.Error("the winhttp override survived")
	}
	if ppath.Exists(content.RecordFilePath(gameDir)) {
		t.Error("the record survived a complete uninstall")
	}
	if again, err := Uninstall(gameDir, nil); err != nil || len(again) != 0 {
		t.Errorf("a second uninstall = %v, %v", again, err)
	}
}

func TestUninstallLeavesAManagerInstalledBepInExAlone(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	if _, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil); err != nil {
		t.Fatal(err)
	}
	// A record with no loader entry: a mod manager installed the loader, and this
	// installer only put levels in and set the prefix override.
	if err := content.ClearRecord(gameDir); err != nil {
		t.Fatal(err)
	}
	prefixName := ppath.Normalize(prefix)
	via := "registry"
	if _, err := content.SaveRecord(gameDir, &content.Record{
		Schema: content.RecordSchema,
		Levels: map[string]content.LevelRecord{
			"mine": {Code: "mine", Filename: "UserData/Levels/mine.mblevel.json"},
		},
		DllOverride: &content.DllOverride{
			Applied: true, Name: proton.WinHTTPDLLName, Value: proton.WinHTTPValue,
			Prefix: &prefixName, Via: &via,
		},
	}); err != nil {
		t.Fatal(err)
	}
	if !proton.WinHTTPOverrideApplied(prefix) {
		t.Fatal("the installer's own override should be in the prefix before the uninstall")
	}

	removed, err := Uninstall(gameDir, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !ppath.IsFile(filepath.Join(gameDir, "winhttp.dll")) || !ppath.IsDir(filepath.Join(gameDir, "dotnet")) {
		t.Errorf("the manager's loader was torn out: removed = %v", removed)
	}
	if proton.WinHTTPOverrideApplied(prefix) {
		t.Error("the override this installer set should still be cleared")
	}
}

func TestDetectReportsTheInstalledVersions(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	if content.ModInstalled(gameDir) {
		t.Fatal("a vanilla directory has no mod")
	}
	if got := Detect(gameDir); got.Installed {
		t.Errorf("Detect on a vanilla directory = %+v", got)
	}
	result, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	got := Detect(gameDir)
	if !got.Installed {
		t.Fatal("the install does not detect")
	}
	if got.ModVersion != modVersion || got.BepInExVersion != bepinexVersion {
		t.Errorf("Detect = %+v", got)
	}
	if !result.State().Installed {
		t.Error("the install result reports its own install as absent")
	}
}

func TestDetectReportsAManagerInstallAsForeign(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	if _, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil); err != nil {
		t.Fatal(err)
	}
	if err := content.ClearRecord(gameDir); err != nil {
		t.Fatal(err)
	}
	state := Detect(gameDir)
	if state.Installed {
		t.Errorf("files without a record are not the installer's: %+v", state)
	}
	if !state.FilesPresent {
		t.Errorf("the plugin files are there, and Detect should say so: %+v", state)
	}
	if !content.ModInstalled(gameDir) {
		t.Error("the plugin files are there, and content.ModInstalled should say so")
	}
}

func TestDryRunChangesNothing(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	result, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine, DryRun: true,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(result.Planned) == 0 {
		t.Fatal("a dry run planned nothing")
	}
	if ppath.IsDir(filepath.Join(gameDir, "BepInEx")) || ppath.Exists(content.RecordFilePath(gameDir)) {
		t.Error("a dry run wrote to the game directory")
	}
	if proton.WinHTTPOverrideApplied(prefix) {
		t.Error("a dry run edited the prefix")
	}
	if stub.downloads() != 0 {
		t.Errorf("a dry run downloaded: %v", stub.log())
	}
}

func TestProgressReportsEveryStep(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	reported := &recorder{cancelAfter: -1}
	if _, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformProton,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, reported); err != nil {
		t.Fatal(err)
	}
	if reported.started < 1 {
		t.Errorf("Start was called %d times", reported.started)
	}
	joined := strings.Join(reported.steps, "\n")
	for _, want := range []string{"BepInEx", "MegabonkLevels"} {
		if !strings.Contains(joined, want) {
			t.Errorf("the checklist should name %q in %v", want, reported.steps)
		}
	}
	if !reported.finished {
		t.Error("the run never finished")
	}
}

func TestCancelRollsBackAPlacedLoader(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	cancel := &recorder{cancelAfter: 4}
	_, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, cancel)
	if !errors.Is(err, ErrCancelled) {
		t.Fatalf("err = %v, want ErrCancelled", err)
	}
	if ppath.IsDir(filepath.Join(gameDir, "BepInEx")) || ppath.IsDir(filepath.Join(gameDir, "dotnet")) {
		t.Error("a cancelled install left the loader behind")
	}
	if ppath.Exists(content.RecordFilePath(gameDir)) {
		t.Error("a cancelled install left a record behind")
	}
	if proton.WinHTTPOverrideApplied(prefix) {
		t.Error("a cancelled install left the prefix edited")
	}
}

func TestInstallWithNoClientRefuses(t *testing.T) {
	if _, err := Install(nil, Options{Game: vanillaGame(t), Platform: PlatformNative}, nil); err == nil {
		t.Error("an install with no client was allowed")
	}
}

func TestUnknownPlatformIsRefused(t *testing.T) {
	stub := newStub(t)
	_, err := Install(stub.client(), Options{
		Game: vanillaGame(t), Prefix: winePrefix(t), Platform: "haiku",
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err == nil || !strings.Contains(err.Error(), "haiku") {
		t.Errorf("an unknown platform = %v", err)
	}
}

func TestInstallRefusesANativeLinuxBuild(t *testing.T) {
	stub := newStub(t)
	dir := filepath.Join(t.TempDir(), "Megabonk")
	writeFile(t, filepath.Join(dir, "Megabonk.x86_64"), "ELF")
	if err := os.MkdirAll(filepath.Join(dir, "Megabonk_Data"), 0o755); err != nil {
		t.Fatal(err)
	}
	_, err := Install(stub.client(), Options{
		Game: dir, Platform: PlatformNative,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err == nil || !strings.Contains(err.Error(), "Linux") {
		t.Errorf("the native Linux build = %v", err)
	}
}

func TestInstallReportsTheFilesItPlaced(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	result, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	want := []string{
		"BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll",
		"BepInEx/plugins/MegabonkLevels/NLayer.LICENSE.txt",
		"BepInEx/plugins/MegabonkLevels/NLayer.dll",
	}
	if !reflect.DeepEqual(result.ModFiles, want) {
		t.Errorf("mod files = %v, want %v", result.ModFiles, want)
	}
	if len(result.PackFiles) == 0 {
		t.Error("the loader pack's files were not reported")
	}
}

func TestCopyButtonCarriesTheExactLaunchOption(t *testing.T) {
	stub := newStub(t)
	reported := &recorder{cancelAfter: -1}
	if _, err := Install(stub.client(), Options{
		Game: vanillaGame(t), Prefix: protonPrefix(t), Platform: PlatformProton,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, reported); err != nil {
		t.Fatal(err)
	}
	if reported.copied != `WINEDLLOVERRIDES="winhttp=n,b" %command%` {
		t.Errorf("copy button = %q", reported.copied)
	}
}

func TestCacheReusesADownloadedArchive(t *testing.T) {
	stub := newStub(t)
	prefix, cache := winePrefix(t), t.TempDir()
	// One game directory, two runs. The first is a new install and fetches both
	// archives; the second is a repair of the same release, which is the run the
	// cache is for.
	gameDir := vanillaGame(t)
	for round := 0; round < 2; round++ {
		if _, err := Install(stub.client(), Options{
			Game: gameDir, Prefix: prefix, Platform: PlatformWine, Cache: cache,
			Pins: map[string]string{bepinexVersion: stub.packDigest},
		}, nil); err != nil {
			t.Fatal(err)
		}
	}
	if stub.downloads() != 2 {
		t.Errorf("two runs on one directory fetched %d archives, want the pack and the mod once each: %v",
			stub.downloads(), stub.log())
	}
	// A second directory needs the archives again: each install unpacks into its
	// own Megabonk_Data/, so a cached copy has to be read back per directory.
	if _, err := Install(stub.client(), Options{
		Game: vanillaGame(t), Prefix: prefix, Platform: PlatformWine, Cache: cache,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil); err != nil {
		t.Fatal(err)
	}
	entries, err := os.ReadDir(cache)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) == 0 {
		t.Fatal("the cache holds nothing")
	}
	for _, entry := range entries {
		if !strings.HasSuffix(entry.Name(), ".zip") {
			t.Errorf("the cache holds %s, want only archives", entry.Name())
		}
	}
}

func TestInstallRefusesWhenTheModIsGone(t *testing.T) {
	stub := newStub(t)
	stub.metadataFails = true
	_, err := Install(stub.client(), Options{
		Game: vanillaGame(t), Prefix: winePrefix(t), Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err == nil {
		t.Fatal("a vanished package was allowed")
	}
	if !strings.Contains(err.Error(), thunderstore.ModName) {
		t.Errorf("the failure should name the package: %v", err)
	}
}

func assertInstalled(t *testing.T, gameDir string) {
	t.Helper()
	for _, name := range []string{
		"BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll",
		"BepInEx/plugins/MegabonkLevels/NLayer.dll",
		"BepInEx/plugins/MegabonkLevels/NLayer.LICENSE.txt",
		"winhttp.dll", "doorstop_config.ini", "changelog.txt", ".doorstop_version",
		"dotnet/coreclr.dll",
	} {
		if !ppath.IsFile(filepath.Join(gameDir, filepath.FromSlash(name))) {
			t.Errorf("%s was not installed", name)
		}
	}
	if !content.ModInstalled(gameDir) {
		t.Error("the mod does not detect as installed")
	}
	record := content.LoadRecord(gameDir)
	if record == nil {
		t.Fatal("no install record")
	}
	if record.ModVersion != modVersion || record.BepinexVersion != bepinexVersion {
		t.Errorf("record versions = %q / %q", record.ModVersion, record.BepinexVersion)
	}
	if record.Loader == nil {
		t.Error("the record carries no loader entry for an installer-managed loader")
	}
}

// recorder stands in for the progress window and records what it was asked to
// show, including the launch option and its copy button.
type recorder struct {
	steps             []string
	started           int
	finished          bool
	launchOptionShown bool
	copied            string
	cancelAfter       int
	done              int
}

func (r *recorder) Start(total int, label string) { r.started++ }

func (r *recorder) Step(label string) {
	r.steps = append(r.steps, label)
	r.done = len(r.steps)
}

func (r *recorder) Finish(message string, ok bool) { r.finished = true }

func (r *recorder) Cancelled() bool {
	// Only the run that means to abort can abort: a plain recorder, left at its
	// zero value, is not a run the user pressed Cancel on.
	return r.cancelAfter >= 0 && len(r.steps) >= r.cancelAfter
}

func (r *recorder) ShowLaunchOption(option string) {
	r.launchOptionShown = true
	r.copied = option
}

// blockingTransport is the guard every test run installs: any request that is
// not aimed at this test's own local server is a failure, so nothing in this
// package can reach Thunderstore by accident.
type blockingTransport struct {
	hit    chan string
	direct http.RoundTripper
}

func (b blockingTransport) RoundTrip(request *http.Request) (*http.Response, error) {
	if !strings.HasPrefix(request.URL.Host, "127.0.0.1:") && !strings.HasPrefix(request.URL.Host, "localhost:") {
		b.hit <- request.URL.String()
		return nil, errors.New("a test tried to reach " + request.URL.String())
	}
	// The transport installed in the package's clients at construction time, so
	// delegating here cannot come back through this one.
	return b.direct.RoundTrip(request)
}

func TestNoTestReachesTheNetwork(t *testing.T) {
	// MEGABONK_THUNDERSTORE_API_URL and ..._CDN_URL point a real client at the
	// public endpoints; make sure a stray value in the environment cannot send a
	// test there either.
	t.Setenv(thunderstore.APIBaseURLEnv, "https://thunderstore.io")
	t.Setenv(thunderstore.CDNBaseURLEnv, "https://gcdn.thunderstore.io")
	hit := make(chan string, 8)
	original := http.DefaultTransport
	http.DefaultTransport = blockingTransport{hit: hit, direct: original}
	defer func() { http.DefaultTransport = original }()

	stub := newStub(t)
	// A client built from the environment has to keep using the test server the
	// caller handed it, not the public origin the environment names.
	client := thunderstore.NewClient(stub.server.URL, stub.server.URL)
	if _, err := Install(client, Options{
		Game: vanillaGame(t), Prefix: winePrefix(t), Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil); err != nil {
		t.Fatal(err)
	}
	select {
	case url := <-hit:
		t.Errorf("a test reached the network at %s", url)
	default:
	}
}

func TestModDigestIsCheckedWhenOneIsHeld(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	_, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins:    map[string]string{bepinexVersion: stub.packDigest},
		ModPins: []ModPin{{Version: modVersion, SHA256: digestOf([]byte("some other archive"))}},
	}, nil)
	if err == nil || !strings.Contains(strings.ToLower(err.Error()), "checksum") {
		t.Errorf("a mod archive that does not match its pin = %v", err)
	}
	if ppath.IsDir(filepath.Join(gameDir, "BepInEx")) {
		t.Error("an unverified mod archive still installed")
	}
}

func TestModArchiveWithoutAPluginSetRefuses(t *testing.T) {
	stub := newStub(t)
	// The client is built after the body is swapped: the stub serves what it holds
	// when the request is made.
	empty := []byte(slurp(t, zipTo(t, filepath.Join(t.TempDir(), "empty.zip"), [][2]string{
		{"manifest.json", `{"name":"Megabonk_Level_Editor"}`},
		{"icon.png", "icon"},
	})))
	stub.modBody = empty
	client := stub.client()
	gameDir, prefix := vanillaGame(t), winePrefix(t)

	_, err := Install(client, Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err == nil || !strings.Contains(err.Error(), "plugin") {
		t.Errorf("a mod archive with no plugin = %v", err)
	}
	// The install is all or nothing: an archive that turns out to carry no plugin
	// takes the loader it unpacked alongside it back out, so the game directory is
	// left as it was rather than half-installed with a loader nothing drives.
	for _, name := range []string{"BepInEx", "dotnet", "winhttp.dll", "doorstop_config.ini",
		content.RecordName} {
		if ppath.Exists(filepath.Join(gameDir, filepath.FromSlash(name))) {
			t.Errorf("%s survived a refused install", name)
		}
	}
	if proton.WinHTTPOverrideApplied(prefix) {
		t.Error("a refused install left the prefix edited")
	}
	// A player's own files are not part of that rollback.
	writeFile(t, filepath.Join(gameDir, "UserData", "Levels", "mine.mblevel.json"), `{"schema":2}`)
	if !ppath.IsFile(filepath.Join(gameDir, "Megabonk.exe")) {
		t.Error("the rollback removed the game")
	}
}

func TestModArchiveWithAnEscapingEntryRefuses(t *testing.T) {
	stub := newStub(t)
	evil := []byte(slurp(t, zipTo(t, filepath.Join(t.TempDir(), "evil.zip"), [][2]string{
		{"BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll", "mod dll"},
		{"BepInEx/plugins/MegabonkLevels/NLayer.dll", "nlayer"},
		{"BepInEx/plugins/MegabonkLevels/NLayer.LICENSE.txt", "license"},
		{"BepInEx/plugins/MegabonkLevels/../../../evil.dll", "evil"},
	})))
	stub.modBody = evil
	client := stub.client()
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	if _, err := Install(client, Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil); err == nil {
		t.Fatal("an escaping mod entry was allowed")
	}
	if ppath.Exists(filepath.Join(gameDir, "..", "evil.dll")) {
		t.Error("the escaping entry was written")
	}
}

func TestPackArchiveMissingTheRuntimeRefuses(t *testing.T) {
	stub := newStub(t)
	// The archive is a zip of something else wearing the loader pack's folder.
	stub.packBody = []byte(slurp(t, zipTo(t, filepath.Join(t.TempDir(), "hollow.zip"), [][2]string{
		{"BepInExPack/README.md", "not a loader"},
	})))
	stub.packDigest = digestOf(stub.packBody)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	_, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err == nil {
		t.Fatal("an archive with no loader in it was allowed")
	}
	if ppath.IsDir(filepath.Join(gameDir, "BepInEx")) || ppath.IsDir(filepath.Join(gameDir, "dotnet")) {
		t.Error("the hollow archive still wrote into the game directory")
	}
}

func TestInstallDetectAndUninstallRoundTripOnACrossOverBottle(t *testing.T) {
	stub := newStub(t)
	gameDir := filepath.Join(t.TempDir(), "CrossOver Bots", "Megabonk", "drive_c",
		"Program Files (x86)", "Steam", "steamapps", "common", "Megabonk")
	writeFile(t, filepath.Join(gameDir, "Megabonk.exe"), "MZ")
	if err := os.MkdirAll(filepath.Join(gameDir, "Megabonk_Data"), 0o755); err != nil {
		t.Fatal(err)
	}
	prefix := bottleOf(t, gameDir)
	if _, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil); err != nil {
		t.Fatal(err)
	}
	state := Detect(gameDir)
	if !state.Installed || state.ModVersion != modVersion || state.BepInExVersion != bepinexVersion {
		t.Fatalf("the bottle install does not detect: %+v", state)
	}
	if state.Platform != PlatformWine {
		t.Errorf("a bottle install reports platform %q", state.Platform)
	}
	if removed, err := Uninstall(gameDir, nil); err != nil || len(removed) == 0 {
		t.Errorf("the bottle uninstall = %v, %v", removed, err)
	}
	if proton.WinHTTPOverrideApplied(prefix) {
		t.Error("the bottle still carries the override")
	}
	if Detect(gameDir).Installed {
		t.Error("the bottle still reports the mod as installed")
	}
}

func TestDetectAgainstNamesTheLatestRelease(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	if _, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil); err != nil {
		t.Fatal(err)
	}
	state := DetectAgainst(stub.client(), gameDir)
	if state.Release != modVersion {
		t.Errorf("latest release = %q, want %q", state.Release, modVersion)
	}
	if state.UpToDate == nil || !*state.UpToDate {
		t.Errorf("an install of the current release should read up to date: %+v", state)
	}
	// An older install is not up to date, and says so.
	if err := content.ClearRecord(gameDir); err != nil {
		t.Fatal(err)
	}
	if _, err := content.SaveRecord(gameDir, &content.Record{Schema: content.RecordSchema,
		ModVersion: "0.1.0", BepinexVersion: bepinexVersion,
		Loader: &content.LoaderState{Installed: true, BepInExVersion: bepinexVersion,
			ModVersion: "0.1.0", PackFiles: []string{"winhttp.dll"}}}); err != nil {
		t.Fatal(err)
	}
	outdated := DetectAgainst(stub.client(), gameDir)
	if outdated.UpToDate == nil || *outdated.UpToDate {
		t.Errorf("an install of 0.1.0 should not read up to date: %+v", outdated)
	}
	if DetectAgainst(nil, gameDir).Release != "" {
		t.Error("DetectAgainst without a client claimed a release")
	}
}

func TestUninstallRestoresAnOverwrittenPluginFile(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	if _, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil); err != nil {
		t.Fatal(err)
	}
	// A run that is aborted partway must not lose the file it was about to
	// replace, and must not leave an override set on a prefix it is walking away
	// from with nothing installed in it.
	plugin := filepath.Join(gameDir, "BepInEx", "plugins", "MegabonkLevels", "MegabonkLevels.Mod.dll")
	writeFile(t, plugin, "the dll from the first install")
	doorstop := filepath.Join(gameDir, "doorstop_config.ini")
	writeFile(t, doorstop, "[UnityDoorstop] the player's own settings")
	if !proton.WinHTTPOverrideApplied(prefix) {
		t.Fatal("the install should have set the override")
	}
	cancel := &recorder{cancelAfter: 3}
	_, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, cancel)
	if err == nil {
		// A run that reached its end before the abort lands is a completed
		// install, and there is nothing to restore.
		t.Skip("the run finished before the abort was asked for")
	}
	if !errors.Is(err, ErrCancelled) {
		t.Fatalf("err = %v, want ErrCancelled", err)
	}
	body, err := os.ReadFile(plugin)
	if err != nil {
		t.Fatalf("the plugin was removed rather than restored: %v", err)
	}
	if string(body) != "the dll from the first install" {
		t.Errorf("the plugin holds %q", body)
	}
	settings, err := os.ReadFile(doorstop)
	if err != nil {
		t.Fatalf("the player's doorstop config was not restored: %v", err)
	}
	if string(settings) != "[UnityDoorstop] the player's own settings" {
		t.Errorf("doorstop_config.ini holds %q", settings)
	}
	if proton.WinHTTPOverrideApplied(prefix) {
		t.Error("the aborted run left its override in the prefix")
	}
	// The record that describes the install still standing is the one from the
	// completed run, not a half-written one from the aborted run.
	if record := content.LoadRecord(gameDir); record == nil || record.ModVersion != modVersion {
		t.Errorf("the aborted run left the record as %+v", record)
	}
}

// The registry writer is the fallback; where wine is on the PATH the override is
// written by wine itself, and the run has to say which one it used.
func TestWinePrefixUsesTheWineBinaryWhenOneIsGiven(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	var calls [][]string
	var seenEnv []string
	result, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins:    map[string]string{bepinexVersion: stub.packDigest},
		WineBin: "/usr/bin/wine",
		Runner: func(argv []string, env map[string]string) int {
			calls = append(calls, argv)
			seenEnv = append(seenEnv, env["WINEPREFIX"])
			return 0
		},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if result.OverrideVia != "wine" {
		t.Errorf("override via = %q, want wine", result.OverrideVia)
	}
	if len(calls) != 1 {
		t.Fatalf("wine was called %d times: %v", len(calls), calls)
	}
	joined := strings.Join(calls[0], " ")
	for _, want := range []string{"/usr/bin/wine", "reg", "add", `HKCU\Software\Wine\DllOverrides`,
		"/v", proton.WinHTTPDLLName, "/d", proton.WinHTTPValue} {
		if !strings.Contains(joined, want) {
			t.Errorf("the registry command %q should carry %q", joined, want)
		}
	}
	if len(seenEnv) != 1 || seenEnv[0] != ppath.Normalize(prefix) {
		t.Errorf("WINEPREFIX = %v", seenEnv)
	}
	// The record names the prefix the override went into, so uninstall can clear
	// it again even though the game folder says nothing about it.
	record := content.LoadRecord(gameDir)
	if record == nil || record.DllOverride == nil || record.DllOverride.Prefix == nil ||
		*record.DllOverride.Prefix != ppath.Normalize(prefix) {
		t.Errorf("the record does not name the prefix: %+v", record)
	}
	if _, err := Uninstall(gameDir, nil); err != nil {
		t.Fatal(err)
	}
	if proton.WinHTTPOverrideApplied(prefix) {
		t.Error("the override written by wine survived the uninstall")
	}
}

// A wine binary that is not there, or that fails, must not be reported as a
// success: the run says registry, which is how the override actually landed.
func TestWinePrefixFallsBackToTheRegistryWriter(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	result, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins:    map[string]string{bepinexVersion: stub.packDigest},
		WineBin: "/usr/bin/wine",
		Runner:  func(argv []string, env map[string]string) int { return 1 },
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if result.OverrideVia != "registry" {
		t.Errorf("override via = %q, want registry", result.OverrideVia)
	}
	value, found := proton.ReadDllOverride(prefix, proton.WinHTTPDLLName, "")
	if !found || value != proton.WinHTTPValue {
		t.Errorf("the fallback did not write the override: %q, %v", value, found)
	}
}

func TestNativeWindowsNeedsNoPrefixAtAll(t *testing.T) {
	stub := newStub(t)
	gameDir := vanillaGame(t)
	result, err := Install(stub.client(), Options{
		Game: gameDir, Platform: PlatformNative,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if result.Prefix != "" {
		t.Errorf("a native install named a prefix: %q", result.Prefix)
	}
	if result.LaunchOption != "" || result.OverrideApplied || result.OverrideVia != "" {
		t.Errorf("a native install touched Wine at all: %+v", result)
	}
	// It is still a complete, detectable, removable install.
	state := Detect(gameDir)
	if !state.Installed || state.Platform != PlatformNative {
		t.Errorf("the native install does not detect: %+v", state)
	}
	if _, err := Uninstall(gameDir, nil); err != nil {
		t.Fatal(err)
	}
	if Detect(gameDir).Installed {
		t.Error("the native install did not uninstall")
	}
}

// A MelonLoader version.dll with no MelonLoader folder behind it is the player's
// or another tool's, and this installer will not move it.
func TestStrayVersionDLLIsLeftAlone(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	writeFile(t, filepath.Join(gameDir, "version.dll"), "not a melon loader proxy")
	_, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err == nil {
		t.Fatal("a proxy nobody can account for was parked silently")
	}
	if !strings.Contains(err.Error(), "version.dll") {
		t.Errorf("the refusal should name the file: %v", err)
	}
	if ppath.Exists(filepath.Join(gameDir, "version.dll.bak")) {
		t.Error("a proxy that is not MelonLoader's was moved aside")
	}
	if !ppath.IsFile(filepath.Join(gameDir, "version.dll")) {
		t.Error("the player's version.dll was removed")
	}
}

// The proxy is parked only when MelonLoader is really there to be replaced, and
// an already-parked proxy is not silently overwritten by a second one.
func TestMelonLoaderProxyIsParkedAndRestored(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	writeFile(t, filepath.Join(gameDir, "version.dll"), "melon loader proxy")
	if err := os.MkdirAll(filepath.Join(gameDir, "MelonLoader", "net6"), 0o755); err != nil {
		t.Fatal(err)
	}
	result, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest},
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !result.ProxyParked {
		t.Fatal("the MelonLoader proxy was left loaded beside the BepInEx proxy")
	}
	if ppath.Exists(filepath.Join(gameDir, "version.dll")) {
		t.Error("both loaders were left active")
	}
	if !ppath.IsFile(filepath.Join(gameDir, "version.dll.bak")) {
		t.Error("the proxy was not parked as version.dll.bak")
	}
	if _, err := Uninstall(gameDir, nil); err != nil {
		t.Fatal(err)
	}
	body, err := os.ReadFile(filepath.Join(gameDir, "version.dll"))
	if err != nil {
		t.Fatalf("version.dll was not restored: %v", err)
	}
	if string(body) != "melon loader proxy" {
		t.Errorf("the restored proxy holds %q", body)
	}
	if ppath.Exists(filepath.Join(gameDir, "version.dll.bak")) {
		t.Error("the parked backup stayed behind")
	}
}

// A game directory that is not a Megabonk install, or is the wrong build, is
// refused before anything is fetched.
func TestRefusesADirectoryThatIsNotTheWindowsGame(t *testing.T) {
	stub := newStub(t)
	for _, tc := range []struct {
		name string
		file string
		want string
	}{
		{name: "native linux build", file: "Megabonk.x86_64", want: "native Linux"},
		{name: "empty folder", file: "", want: "does not look like a Megabonk install"},
	} {
		t.Run(tc.name, func(t *testing.T) {
			dir := t.TempDir()
			if tc.file != "" {
				writeFile(t, filepath.Join(dir, tc.file), "ELF")
				if err := os.MkdirAll(filepath.Join(dir, "Megabonk_Data"), 0o755); err != nil {
					t.Fatal(err)
				}
			}
			_, err := Install(stub.client(), Options{
				Game: dir, Platform: PlatformNative,
				Pins: map[string]string{bepinexVersion: stub.packDigest},
			}, nil)
			if err == nil || !strings.Contains(err.Error(), tc.want) {
				t.Errorf("%s = %v, want it to mention %q", tc.name, err, tc.want)
			}
			if stub.downloads() != 0 {
				t.Errorf("%s was still downloaded for: %v", tc.name, stub.log())
			}
		})
	}
}

// The built-in pin table is what lets a player install with no digest on the
// command line at all: the run resolves the loader pack version the release
// depends on, and that version's known-good digest travels with the resolution so
// the archive is checked against it. A version the table does not know travels
// with nothing, and the install refuses it.
func TestResolutionCarriesTheBuiltInPin(t *testing.T) {
	stub := newStub(t)
	stub.bepinexVersion = builtinBepInExVersion
	resolution, err := stub.client().Resolve()
	if err != nil {
		t.Fatal(err)
	}
	want, pinned := thunderstore.PinnedBepInExDigest(builtinBepInExVersion)
	if !pinned {
		t.Fatalf("the installer should ship a digest for %s", builtinBepInExVersion)
	}
	if resolution.BepInExPinnedSHA != want {
		t.Errorf("the resolution carries %q, want the built-in %q", resolution.BepInExPinnedSHA, want)
	}

	// A version the table has never heard of carries no digest, and the install
	// refuses it rather than writing an archive it cannot verify.
	unknown := newStub(t)
	unknown.bepinexVersion = "9.9.9"
	unknownResolution, err := unknown.client().Resolve()
	if err != nil {
		t.Fatal(err)
	}
	if unknownResolution.BepInExPinnedSHA != "" {
		t.Errorf("an unpinned version carried %q", unknownResolution.BepInExPinnedSHA)
	}
	_, err = Install(unknown.client(), Options{
		Game: vanillaGame(t), Prefix: winePrefix(t), Platform: PlatformWine,
	}, nil)
	if err == nil || !strings.Contains(err.Error(), "SHA-256") {
		t.Errorf("an unknown loader pack version = %v, want a refusal naming the digest", err)
	}
	if stub.downloads() != 0 || unknown.downloads() != 0 {
		t.Errorf("an unresolvable or unverifiable pack was still downloaded: %v %v",
			stub.log(), unknown.log())
	}
}

// A caller that passes --bepinex-sha256 overrides the built-in table, which is how
// a player installs a loader pack release the shipped installer has never heard
// of. The override is checked too: it is not a way to skip verification.
func TestCallerPinOverridesTheBuiltInTable(t *testing.T) {
	stub := newStub(t)
	stub.bepinexVersion = builtinBepInExVersion
	gameDir, prefix := vanillaGame(t), winePrefix(t)

	// The stub's pack is not the real 6.0.788, so the built-in digest would refuse
	// it; the caller's digest is what this run has to honour.
	result, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{builtinBepInExVersion: stub.packDigest},
	}, nil)
	if err != nil {
		t.Fatalf("an explicit --bepinex-sha256 should win over the built-in pin: %v", err)
	}
	if result.BepInExVersion != builtinBepInExVersion {
		t.Errorf("loader pack version = %q", result.BepInExVersion)
	}
	// A wrong caller-supplied digest is still refused, built-in table or not.
	if _, err := Install(stub.client(), Options{
		Game: vanillaGame(t), Prefix: winePrefix(t), Platform: PlatformWine,
		Pins: map[string]string{builtinBepInExVersion: digestOf([]byte("not the archive"))},
	}, nil); err == nil || !strings.Contains(strings.ToLower(err.Error()), "checksum") {
		t.Errorf("a wrong explicit digest = %v", err)
	}
}

// A --mod-sha256 that the archive does not carry stops the run; Thunderstore
// publishes no checksum for the mod, so the caller's digest is the only thing
// that can prove the bytes.
func TestModPinFromTheCallerIsEnforced(t *testing.T) {
	stub := newStub(t)
	// Right digest: the run goes through and records it.
	result, err := Install(stub.client(), Options{
		Game: vanillaGame(t), Prefix: winePrefix(t), Platform: PlatformWine,
		Pins:    map[string]string{bepinexVersion: stub.packDigest},
		ModPins: []ModPin{{Version: modVersion, SHA256: stub.modDigest}},
	}, nil)
	if err != nil {
		t.Fatalf("a matching --mod-sha256 should install: %v", err)
	}
	if result.ModSHA256 != stub.modDigest {
		t.Errorf("recorded mod digest = %q, want %q", result.ModSHA256, stub.modDigest)
	}
	record := content.LoadRecord(vanillaGameOf(t, result))
	if record == nil || record.Loader == nil || record.Loader.ModSHA256 != stub.modDigest {
		t.Errorf("the record did not keep the verified digest: %+v", record)
	}
}
