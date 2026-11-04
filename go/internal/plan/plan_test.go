package plan

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/content"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/manifest"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/proton"
)

func digestOf(body string) string {
	sum := sha256.Sum256([]byte(body))
	return hex.EncodeToString(sum[:])
}

func write(t *testing.T, path, body string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

func writeZipFile(t *testing.T, path string, entries map[string]string) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	handle, err := os.Create(path)
	if err != nil {
		t.Fatal(err)
	}
	zipWriter := zip.NewWriter(handle)
	for _, name := range sortedKeys(entries) {
		member, err := zipWriter.Create(name)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := member.Write([]byte(entries[name])); err != nil {
			t.Fatal(err)
		}
	}
	if err := zipWriter.Close(); err != nil {
		t.Fatal(err)
	}
	if err := handle.Close(); err != nil {
		t.Fatal(err)
	}
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	sum := sha256.Sum256(raw)
	return hex.EncodeToString(sum[:])
}

func sortedKeys(entries map[string]string) []string {
	keys := make([]string, 0, len(entries))
	for key := range entries {
		keys = append(keys, key)
	}
	for i := 1; i < len(keys); i++ {
		for j := i; j > 0 && keys[j] < keys[j-1]; j-- {
			keys[j], keys[j-1] = keys[j-1], keys[j]
		}
	}
	return keys
}

// makePackage mirrors _package in tests/test_player_installer_plan.py.
func makePackage(t *testing.T) string {
	t.Helper()
	packageDir := filepath.Join(t.TempDir(), "package")
	loaderDigest := writeZipFile(t, filepath.Join(packageDir, "vendor", "MelonLoader.x64.zip"), map[string]string{
		"version.dll":                                     "MZ",
		"MelonLoader/net6/MelonLoader.dll":                "MZ",
		"MelonLoader/net6/MelonLoader.runtimeconfig.json": "{}",
	})
	runtimeDigest := writeZipFile(t, filepath.Join(packageDir, "vendor", "dotnet-runtime-6.0.36-win-x64.zip"), map[string]string{
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
			map[string]any{"name": "MelonLoader.x64.zip", "url": "u", "sha256": loaderDigest, "kind": "melonloader", "version": "0.7.3"},
			map[string]any{"name": "dotnet-runtime-6.0.36-win-x64.zip", "url": "u", "sha256": runtimeDigest, "kind": "dotnet", "version": "6.0.36"},
		},
		"files": []any{
			map[string]any{"path": "mod/MegabonkLevels.Mod.dll", "sha256": digestOf("mod dll"), "dest": "Mods/MegabonkLevels.Mod.dll"},
			map[string]any{"path": "mod/MegabonkLevels.Mod.pdb", "sha256": digestOf("pdb"), "dest": "Mods/MegabonkLevels.Mod.pdb"},
			map[string]any{"path": "mod/NLayer.dll", "sha256": digestOf("nlayer"), "dest": "Mods/NLayer.dll"},
			map[string]any{"path": "mod/NLayer.dll", "sha256": digestOf("nlayer"), "dest": "UserLibs/NLayer.dll"},
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

func makePrefix(t *testing.T) string {
	t.Helper()
	prefix := filepath.Join(t.TempDir(), "compatdata", "3405340", "pfx")
	if err := os.MkdirAll(filepath.Join(prefix, "drive_c"), 0o755); err != nil {
		t.Fatal(err)
	}
	return prefix
}

func options(game, prefix string) Options {
	return Options{Game: game, Prefix: prefix, RuntimeMode: RuntimeModePrefix, DllOverride: "auto", WineOverride: "auto", Verify: false}
}

func kinds(actions []Action) []string {
	out := []string{}
	for _, action := range actions {
		out = append(out, action.Kind)
	}
	return out
}

func countKind(actions []Action, kind string) int {
	total := 0
	for _, action := range actions {
		if action.Kind == kind {
			total++
		}
	}
	return total
}

func loadManifest(t *testing.T, packageDir string) *manifest.Package {
	t.Helper()
	loaded, err := manifest.LoadManifest(ppath.Join(packageDir, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	return loaded
}

func TestFreshInstallPlansEveryPiece(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	built, err := BuildPlan(packageDir, Options{Manifest: loadManifest(t, packageDir), Game: game, Prefix: prefix, RuntimeMode: RuntimeModePrefix, DllOverride: "auto", WineOverride: "auto"})
	if err != nil {
		t.Fatal(err)
	}
	got := kinds(built.Actions)
	for _, want := range []string{"install-loader", "install-runtime", "enable-dll-override", "create-levels-dir"} {
		if !contains(got, want) {
			t.Errorf("kinds = %v, want %s", got, want)
		}
	}
	if count := countKind(built.Actions, "install-file"); count != 4 {
		t.Errorf("install-file steps = %d in %v, want 4", count, got)
	}
	if built.IsNoop() {
		t.Error("a vanilla directory is not a no-op")
	}
	if built.LaunchOption != nil {
		t.Errorf("a prefix install needs no launch option, got %q", *built.LaunchOption)
	}
}

func TestSecondRunDoesNothing(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	pkg := loadManifest(t, packageDir)
	built, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, Prefix: prefix, DllOverride: "auto", WineOverride: "auto"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	again, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, Prefix: prefix, DllOverride: "auto", WineOverride: "auto"})
	if err != nil {
		t.Fatal(err)
	}
	if !again.IsNoop() {
		t.Errorf("a second run plans %v", kinds(again.Actions))
	}
}

func TestRepairReplacesOnlyWhatChanged(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	pkg := loadManifest(t, packageDir)
	built, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, Prefix: prefix, DllOverride: "auto", WineOverride: "auto"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	tampered := filepath.Join(game, "Mods", "MegabonkLevels.Mod.dll")
	write(t, tampered, "corrupted")
	os.Remove(filepath.Join(game, "UserLibs", "NLayer.dll"))

	repair, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, Prefix: prefix, DllOverride: "auto", WineOverride: "auto"})
	if err != nil {
		t.Fatal(err)
	}
	if len(repair.Actions) != 2 {
		t.Fatalf("repair plans %v", repair.Actions)
	}
	if repair.Actions[0].Path != ppath.Join(game, "Mods", "MegabonkLevels.Mod.dll") ||
		repair.Actions[1].Path != ppath.Join(game, "UserLibs", "NLayer.dll") {
		t.Errorf("repair = %+v", repair.Actions)
	}
	if _, err := ApplyPlan(repair, nil); err != nil {
		t.Fatal(err)
	}
	body, err := os.ReadFile(tampered)
	if err != nil || string(body) != "mod dll" {
		t.Errorf("the tampered file = %q, %v", body, err)
	}
}

func TestGamedirFallbackWithoutAUsablePrefix(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	missing := filepath.Join(t.TempDir(), "compatdata", "3405340", "pfx")
	built, err := BuildPlan(packageDir, Options{Manifest: loadManifest(t, packageDir), Game: game, Prefix: missing, DllOverride: "auto", WineOverride: "auto"})
	if err != nil {
		t.Fatal(err)
	}
	if built.RuntimeMode != RuntimeModeGameDir {
		t.Errorf("mode = %q", built.RuntimeMode)
	}
	if len(built.Warnings) != 2 {
		t.Fatalf("warnings = %v", built.Warnings)
	}
	if !strings.Contains(built.Warnings[0], "no usable Proton prefix at "+missing) ||
		!strings.Contains(built.Warnings[0], "beside the game") {
		t.Errorf("warning = %q", built.Warnings[0])
	}
	if !strings.Contains(built.Warnings[1], "pass --prefix <path to the pfx directory>") {
		t.Errorf("warning = %q", built.Warnings[1])
	}
	if built.LaunchOption == nil || !strings.Contains(*built.LaunchOption, "DOTNET_ROOT=Z:") {
		t.Errorf("launch option = %v", built.LaunchOption)
	}
	if built.DllOverride {
		t.Error("a gamedir install sets no dll override")
	}
	for _, action := range built.Actions {
		if action.Kind == "install-runtime" && !strings.Contains(action.Detail, "Steam launch option") {
			t.Errorf("the runtime step should repeat the launch option: %q", action.Detail)
		}
	}
}

func TestBuildPlanRefusesABrokenRequest(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	pkg := loadManifest(t, packageDir)

	if _, err := BuildPlan(packageDir, Options{Manifest: pkg, DllOverride: "auto"}); err == nil ||
		!strings.Contains(err.Error(), "no game directory") {
		t.Errorf("no game = %v", err)
	}
	if _, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, RuntimeMode: "system", DllOverride: "auto"}); err == nil ||
		!strings.Contains(err.Error(), "unknown runtime mode") || !strings.Contains(err.Error(), "prefix, gamedir") {
		t.Errorf("bad mode = %v", err)
	}

	native := filepath.Join(t.TempDir(), "native")
	if err := os.MkdirAll(filepath.Join(native, "Megabonk_Data"), 0o755); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(native, "Megabonk.x86_64"), "ELF")
	if _, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: native, DllOverride: "auto"}); err == nil ||
		!strings.Contains(err.Error(), "Linux native build") {
		t.Errorf("native build = %v", err)
	}
}

func TestFileActionsNameAMissingPackageFile(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	os.Remove(filepath.Join(packageDir, "mod", "NLayer.dll"))
	_, err := BuildPlan(packageDir, Options{Manifest: loadManifest(t, packageDir), Game: game, DllOverride: "auto"})
	if err == nil || !strings.Contains(err.Error(), "NLayer.dll is missing from the package") ||
		!strings.Contains(err.Error(), "mod/NLayer.dll") {
		t.Errorf("err = %v", err)
	}
}

func TestVerifyRefusesATamperedPackage(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	write(t, filepath.Join(packageDir, "mod", "NLayer.dll"), "trojan")
	_, err := BuildPlan(packageDir, Options{Manifest: loadManifest(t, packageDir), Game: game, DllOverride: "auto", Verify: true})
	if err == nil || !strings.Contains(err.Error(), "does not match its manifest") ||
		!strings.Contains(err.Error(), "NLayer.dll") {
		t.Errorf("err = %v", err)
	}
}

func TestLevelAndPackSteps(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	pkg := loadManifest(t, packageDir)
	root := t.TempDir()

	level := filepath.Join(root, "skate.mblevel.json")
	write(t, level, `{"schema": 2, "name": "Skate Plaza"}`)
	built, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, DllOverride: "auto", Level: level})
	if err != nil {
		t.Fatal(err)
	}
	target := ppath.Join(content.LevelsPath(game), "skate.mblevel.json")
	found := false
	for _, action := range built.Actions {
		if action.Kind == "install-file" && action.Path == target {
			found = true
		}
	}
	if !found {
		t.Errorf("the level is not in %v", built.Actions)
	}
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	again, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, DllOverride: "auto", Level: level})
	if err != nil {
		t.Fatal(err)
	}
	for _, action := range again.Actions {
		if action.Path == target {
			t.Errorf("an installed level should not be recopied: %v", again.Actions)
		}
	}

	bad := filepath.Join(root, "bad.mblevel.json")
	write(t, bad, `{`)
	if _, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, DllOverride: "auto", Level: bad}); err == nil ||
		!strings.Contains(err.Error(), "bad.mblevel.json") {
		t.Errorf("an invalid level = %v", err)
	}

	source := filepath.Join(root, "packsrc", "thps")
	write(t, filepath.Join(source, "thps"), "bundle")
	write(t, filepath.Join(source, "manifest.json"),
		`{"id": "thps", "name": "THPS", "author": "user", "version": "1", "assets": ["a"]}`)
	packPlan, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, DllOverride: "auto", Pack: source})
	if err != nil {
		t.Fatal(err)
	}
	if countKind(packPlan.Actions, "install-file") == 0 {
		t.Error("the pack contributes no files")
	}
	if _, err := ApplyPlan(packPlan, nil); err != nil {
		t.Fatal(err)
	}
	if !ppath.IsFile(filepath.Join(game, "UserData", "LevelPacks", "thps", "thps")) {
		t.Error("the bundle was not installed")
	}
}

func TestApplyWritesTheRecordTheReferenceWrites(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	pkg := loadManifest(t, packageDir)
	built, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, Prefix: prefix, DllOverride: "auto", WineOverride: "registry"})
	if err != nil {
		t.Fatal(err)
	}
	taken, err := ApplyPlan(built, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(taken) != len(built.Actions) {
		t.Errorf("taken = %d, planned = %d", len(taken), len(built.Actions))
	}
	record := content.LoadRecord(game)
	if record == nil {
		t.Fatal("no record was written")
	}
	if record.Schema != content.RecordSchema || record.PackageID != pkg.PackageID || record.GameBuildID != "21750826" {
		t.Errorf("identity = %+v", record)
	}
	if record.GameDir != ppath.Normalize(game) {
		t.Errorf("game_dir = %q", record.GameDir)
	}
	wantFiles := []string{"Mods/MegabonkLevels.Mod.dll", "Mods/MegabonkLevels.Mod.pdb", "Mods/NLayer.dll", "UserLibs/NLayer.dll"}
	if !reflect.DeepEqual(record.Files, wantFiles) {
		t.Errorf("files = %v, want %v", record.Files, wantFiles)
	}
	if record.Runtime == nil || record.Runtime.Mode != RuntimeModePrefix || record.Runtime.Version != "6.0.36" ||
		record.Runtime.Path != proton.RuntimeTarget(prefix) {
		t.Errorf("runtime = %+v", record.Runtime)
	}
	if record.DllOverride == nil || !record.DllOverride.Applied || record.DllOverride.Via == nil ||
		*record.DllOverride.Via != "registry" || record.DllOverride.Prefix == nil || *record.DllOverride.Prefix != prefix {
		t.Errorf("dll_override = %+v", record.DllOverride)
	}
	if !proton.RuntimeInstalled(proton.RuntimeTarget(prefix), "6.0.36") {
		t.Error("the runtime is not where the record says it is")
	}
	if content.InstalledLoaderVersion(game) != "0.7.3" {
		t.Error("the loader marker was not written")
	}
	if value, ok := proton.ReadDllOverride(prefix, proton.DLLName, ""); !ok || value != proton.DLLValue {
		t.Errorf("override = %q, %v", value, ok)
	}
}

func TestApplyRecordsLevelsAndPacks(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	pkg := loadManifest(t, packageDir)
	root := t.TempDir()
	level := filepath.Join(root, "a.mblevel.json")
	write(t, level, `{"schema": 2}`)
	source := filepath.Join(root, "packsrc", "thps")
	write(t, filepath.Join(source, "thps"), "bundle")
	write(t, filepath.Join(source, "manifest.json"),
		`{"id": "thps", "name": "THPS", "author": "user", "version": "1", "assets": ["a"]}`)

	built, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, Prefix: prefix, DllOverride: "auto", Level: level, Pack: source})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	record := content.LoadRecord(game)
	if record == nil {
		t.Fatal("no record was written")
	}
	if !reflect.DeepEqual(record.Levels, []string{"UserData/Levels/a.mblevel.json"}) {
		t.Errorf("levels = %v", record.Levels)
	}
	entry, found := record.Packs["thps"]
	if !found || entry.Dir != "UserData/LevelPacks/thps" || !reflect.DeepEqual(entry.Files, []string{
		"UserData/LevelPacks/thps/manifest.json", "UserData/LevelPacks/thps/thps"}) {
		t.Errorf("packs = %+v", record.Packs)
	}
}

func TestUninstallTakesBackWhatItPlaced(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	pkg := loadManifest(t, packageDir)
	root := t.TempDir()
	level := filepath.Join(root, "a.mblevel.json")
	write(t, level, `{"schema": 2}`)
	built, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, Prefix: prefix, DllOverride: "auto", Level: level})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	playerFile := filepath.Join(game, "UserData", "Levels", "mine.mblevel.json")
	write(t, playerFile, `{"schema": 2}`)

	removed, err := Uninstall(game, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(removed) == 0 {
		t.Fatal("nothing was removed")
	}
	for _, gone := range []string{
		filepath.Join(game, "MelonLoader"),
		filepath.Join(game, "version.dll"),
		filepath.Join(game, "Mods", "MegabonkLevels.Mod.dll"),
		filepath.Join(game, "UserData", "Levels", "a.mblevel.json"),
		filepath.Join(game, content.RecordName),
	} {
		if ppath.Exists(gone) {
			t.Errorf("%s survived the uninstall", ppath.Name(gone))
		}
	}
	if !ppath.Exists(playerFile) {
		t.Error("the player's own level was removed")
	}
	if ppath.Exists(proton.RuntimeTarget(prefix)) {
		t.Error("the .NET runtime survived")
	}
	if _, ok := proton.ReadDllOverride(prefix, proton.DLLName, ""); ok {
		t.Error("the version.dll override survived")
	}
	if removedAgain, err := Uninstall(game, nil); err != nil || len(removedAgain) != 0 {
		t.Errorf("a second uninstall = %v, %v", removedAgain, err)
	}
}

func TestUninstallLeavesAVanillaDirectoryAlone(t *testing.T) {
	game := makeGame(t)
	removed, err := Uninstall(game, nil)
	if err != nil || len(removed) != 0 {
		t.Errorf("removed = %v, err = %v", removed, err)
	}
}

func TestLoaderArchiveRefusesAnEscapingEntry(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	digest := writeZipFile(t, filepath.Join(packageDir, "vendor", "MelonLoader.x64.zip"), map[string]string{
		"../../evil.dll":         "MZ",
		"MelonLoader/net6/x.dll": "MZ",
		"version.dll":            "MZ",
	})
	document, err := os.ReadFile(filepath.Join(packageDir, "manifest.json"))
	if err != nil {
		t.Fatal(err)
	}
	var raw map[string]any
	if err := json.Unmarshal(document, &raw); err != nil {
		t.Fatal(err)
	}
	for _, entry := range raw["vendors"].([]any) {
		vendor := entry.(map[string]any)
		if vendor["kind"] == "melonloader" {
			vendor["sha256"] = digest
		}
	}
	rewritten, err := json.Marshal(raw)
	if err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(packageDir, "manifest.json"), string(rewritten))

	built, err := BuildPlan(packageDir, Options{Manifest: loadManifest(t, packageDir), Game: game, Prefix: prefix, DllOverride: "auto"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(built, nil); err == nil ||
		!strings.Contains(err.Error(), "would escape the game directory") ||
		!strings.Contains(err.Error(), "evil.dll") {
		t.Errorf("err = %v", err)
	}
	if ppath.Exists(filepath.Join(game, "..", "evil.dll")) {
		t.Error("the escaping entry was written")
	}
}

func TestWineOverrideModeNeedsAWineBinary(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	root := t.TempDir()
	prefix := filepath.Join(root, "library", "steamapps", "compatdata", "3405340", "pfx")
	if err := os.MkdirAll(filepath.Join(prefix, "drive_c"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "library", "steamapps", "common", "Proton 10.0"), 0o755); err != nil {
		t.Fatal(err)
	}
	pkg := loadManifest(t, packageDir)
	built, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, Prefix: prefix, DllOverride: "auto", WineOverride: "wine"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(built, nil); err == nil ||
		!strings.Contains(err.Error(), "no wine binary found in the Proton tools under") ||
		!strings.Contains(err.Error(), ppath.Join(root, "library")) {
		t.Errorf("err = %v", err)
	}

	wine := filepath.Join(root, "library", "steamapps", "common", "Proton 10.0", "files", "bin", "wine")
	write(t, wine, "#!/bin/sh\nexit 0\n")
	if err := os.Chmod(wine, 0o755); err != nil {
		t.Fatal(err)
	}
	again, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, Prefix: prefix, DllOverride: "auto", WineOverride: "wine"})
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(again, nil); err != nil {
		t.Errorf("with a wine binary the override should go through: %v", err)
	}
	record := content.LoadRecord(game)
	if record == nil || record.DllOverride == nil {
		t.Fatalf("dll_override = %+v", record)
	}
	if record.DllOverride.Via == nil || *record.DllOverride.Via != "wine" {
		t.Errorf("via = %v", record.DllOverride.Via)
	}
}

func TestOverrideOffPlansNoRegistryStep(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	pkg := loadManifest(t, packageDir)
	built, err := BuildPlan(packageDir, Options{Manifest: pkg, Game: game, Prefix: prefix, DllOverride: "off", WineOverride: "off"})
	if err != nil {
		t.Fatal(err)
	}
	if countKind(built.Actions, "enable-dll-override") != 0 {
		t.Errorf("kinds = %v", kinds(built.Actions))
	}
	if built.DllOverride {
		t.Error("dll_override should be false")
	}
}

func TestLibraryForPrefixClimbsToTheLibrary(t *testing.T) {
	prefix := "/library/steamapps/compatdata/3405340/pfx"
	if got := libraryForPrefix(prefix); got != "/library" {
		t.Errorf("library = %q", got)
	}
	if got := libraryForPrefix("/somewhere/else/Megabonk"); got != "" {
		t.Errorf("a path outside compatdata = %q", got)
	}
}

func TestRelativeKeepsForeignPathsWhole(t *testing.T) {
	if got := relative("/game", "/game/UserData/Levels/a.json"); got != "UserData/Levels/a.json" {
		t.Errorf("relative = %q", got)
	}
	if got := relative("/game", "/other/a.json"); got != "/other/a.json" {
		t.Errorf("a path outside the game = %q", got)
	}
}

// TestResolveKeepsSlashSemanticsOnWindows replays the Windows shape of
// filepath.Abs (backslashes), a working ToSlash, and a failing EvalSymlinks:
// the exact shape a zip member that does not exist yet produces there.
func TestResolveKeepsSlashSemanticsOnWindows(t *testing.T) {
	windowsAbs := func(p string) (string, error) { return strings.ReplaceAll(p, "/", `\`), nil }
	windowsToSlash := func(p string) string { return strings.ReplaceAll(p, `\`, "/") }
	missing := func(string) (string, error) { return "", os.ErrNotExist }
	member := "C:/work/game/Megabonk/MelonLoader/net6/MelonLoader.dll"
	if got := resolveWith(member, windowsAbs, windowsToSlash, missing); got != member {
		t.Errorf("resolveWith = %q, want the slash form", got)
	}
	nativeEval := func(p string) (string, error) { return strings.ReplaceAll(p, "/", `\`), nil }
	if got := resolveWith(member, windowsAbs, windowsToSlash, nativeEval); got != member {
		t.Errorf("resolveWith through EvalSymlinks = %q, want the slash form", got)
	}
}

func TestDocumentShapeForJSON(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	built, err := BuildPlan(packageDir, Options{Manifest: loadManifest(t, packageDir), Game: game, Prefix: prefix, DllOverride: "auto"})
	if err != nil {
		t.Fatal(err)
	}
	document := built.Document()
	if document.PackageID != "megabonk-levels-0.0.1-ml0.7.3-linux" || document.Build != "windows" {
		t.Errorf("document = %+v", document)
	}
	if document.Prefix == nil || *document.Prefix != prefix {
		t.Errorf("prefix = %v", document.Prefix)
	}
	body, err := json.Marshal(document)
	if err != nil {
		t.Fatal(err)
	}
	var decoded map[string]any
	if err := json.Unmarshal(body, &decoded); err != nil {
		t.Fatal(err)
	}
	for _, key := range []string{"package", "package_id", "game_dir", "runtime_mode", "actions", "warnings", "launch_option"} {
		if _, found := decoded[key]; !found {
			t.Errorf("%s is missing from %s", key, body)
		}
	}
	actions, _ := decoded["actions"].([]any)
	if len(actions) == 0 {
		t.Fatal("no actions in the document")
	}
	first := actions[0].(map[string]any)
	if _, found := first["source"]; !found {
		t.Errorf("a step with a source should carry one: %v", first)
	}
}

func nativeOptions(game string) Options {
	return Options{Game: game, RuntimeMode: RuntimeModeNative, DllOverride: "auto", WineOverride: "auto"}
}

func TestNativeModePlacesTheRuntimeUnderTheLoaderWithoutWineSteps(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	opts := nativeOptions(game)
	opts.Prefix = makePrefix(t)
	built, err := BuildPlan(packageDir, opts)
	if err != nil {
		t.Fatal(err)
	}
	want := filepath.ToSlash(filepath.Join(game, "MelonLoader", "Dependencies", "dotnet"))
	if built.RuntimeMode != RuntimeModeNative || built.RuntimeTarget != want {
		t.Errorf("mode = %q, target = %q, want %q", built.RuntimeMode, built.RuntimeTarget, want)
	}
	if built.LaunchOption != nil || built.DllOverride || len(built.Warnings) != 0 {
		t.Errorf("launch = %v, override = %v, warnings = %v", built.LaunchOption, built.DllOverride, built.Warnings)
	}
	for _, action := range built.Actions {
		if action.Kind == "enable-dll-override" {
			t.Errorf("native mode must not touch a Wine prefix: %+v", action)
		}
		if action.Kind == "install-runtime" && strings.Contains(action.Detail, "launch option") {
			t.Errorf("runtime step mentions a launch option: %q", action.Detail)
		}
	}
}

func TestNativeInstallIsANoopOnRerunAndRepairsOnlyTheRuntime(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	opts := nativeOptions(game)
	built, err := BuildPlan(packageDir, opts)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	if hostfxr := filepath.Join(game, "MelonLoader", "Dependencies", "dotnet", "host", "fxr", "6.0.36", "hostfxr.dll"); !ppathIsFile(hostfxr) {
		t.Fatalf("runtime not placed: %s", hostfxr)
	}
	again, err := BuildPlan(packageDir, opts)
	if err != nil {
		t.Fatal(err)
	}
	if !again.IsNoop() {
		t.Fatalf("rerun actions = %v", kinds(again.Actions))
	}
	record := content.LoadRecord(ppath.Normalize(game))
	if record == nil || record.Runtime == nil || record.Runtime.Mode != RuntimeModeNative || record.Runtime.LaunchOption != nil {
		t.Fatalf("record runtime = %+v", record)
	}
	if err := os.RemoveAll(filepath.Join(game, "MelonLoader", "Dependencies", "dotnet")); err != nil {
		t.Fatal(err)
	}
	repair, err := BuildPlan(packageDir, opts)
	if err != nil {
		t.Fatal(err)
	}
	if got := kinds(repair.Actions); !reflect.DeepEqual(got, []string{"install-runtime"}) {
		t.Errorf("repair = %v", got)
	}
}

func TestNativeUninstallRestoresAVanillaGame(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	built, err := BuildPlan(packageDir, nativeOptions(game))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(game, "UserData", "Loader.cfg"), "[loader]")
	if err := os.MkdirAll(filepath.Join(game, "Plugins"), 0o755); err != nil {
		t.Fatal(err)
	}
	if _, err := Uninstall(game, nil); err != nil {
		t.Fatal(err)
	}
	entries, err := os.ReadDir(game)
	if err != nil {
		t.Fatal(err)
	}
	var names []string
	for _, entry := range entries {
		names = append(names, entry.Name())
	}
	if want := []string{"Megabonk.exe", "Megabonk_Data"}; !reflect.DeepEqual(names, want) {
		t.Errorf("game dir after uninstall = %v, want %v", names, want)
	}
}

func TestUninstallKeepsWhatAPlayerPutInPluginsAndUserData(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	built, err := BuildPlan(packageDir, nativeOptions(game))
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	write(t, filepath.Join(game, "UserData", "Loader.cfg"), "[loader]")
	write(t, filepath.Join(game, "Plugins", "Other.dll"), "plugin")
	write(t, filepath.Join(game, "UserData", "MelonPreferences.cfg"), "prefs")
	if _, err := Uninstall(game, nil); err != nil {
		t.Fatal(err)
	}
	for _, kept := range []string{"Plugins/Other.dll", "UserData/MelonPreferences.cfg"} {
		if !ppathIsFile(filepath.Join(game, filepath.FromSlash(kept))) {
			t.Errorf("%s was removed", kept)
		}
	}
	if ppathIsFile(filepath.Join(game, "UserData", "Loader.cfg")) {
		t.Error("the loader's own Loader.cfg survived")
	}
}

func ppathIsFile(path string) bool { return ppath.IsFile(ppath.Normalize(filepath.ToSlash(path))) }

func wineOptions(game, prefix string) Options {
	return Options{Game: game, Prefix: prefix, RuntimeMode: RuntimeModeWine, DllOverride: "auto", WineOverride: "auto"}
}

func TestWineModePlacesTheRuntimeUnderTheLoaderAndOverridesTheShim(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	built, err := BuildPlan(packageDir, wineOptions(game, prefix))
	if err != nil {
		t.Fatal(err)
	}
	want := filepath.ToSlash(filepath.Join(game, "MelonLoader", "Dependencies", "dotnet"))
	if built.RuntimeMode != RuntimeModeWine || built.RuntimeTarget != want {
		t.Errorf("mode = %q, target = %q, want %q", built.RuntimeMode, built.RuntimeTarget, want)
	}
	if built.LaunchOption != nil || !built.DllOverride || len(built.Warnings) != 0 {
		t.Errorf("launch = %v, override = %v, warnings = %v", built.LaunchOption, built.DllOverride, built.Warnings)
	}
	if countKind(built.Actions, "enable-dll-override") != 1 {
		t.Errorf("actions = %v", kinds(built.Actions))
	}
}

func TestWineModeNeedsAPrefix(t *testing.T) {
	packageDir, game := makePackage(t), makeGame(t)
	if _, err := BuildPlan(packageDir, wineOptions(game, "")); err == nil || !strings.Contains(err.Error(), "--prefix") {
		t.Fatalf("err = %v", err)
	}
}

func TestWineInstallIsANoopOnRerunAndUninstallClearsTheOverride(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	opts := wineOptions(game, prefix)
	built, err := BuildPlan(packageDir, opts)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	if value, found := proton.ReadDllOverride(ppath.Normalize(prefix), proton.DLLName, ""); !found || value != proton.DLLValue {
		t.Fatalf("override = %q, found = %v", value, found)
	}
	again, err := BuildPlan(packageDir, opts)
	if err != nil {
		t.Fatal(err)
	}
	if !again.IsNoop() {
		t.Fatalf("rerun actions = %v", kinds(again.Actions))
	}
	record := content.LoadRecord(ppath.Normalize(game))
	if record == nil || record.Runtime == nil || record.Runtime.Mode != RuntimeModeWine || record.DllOverride == nil || record.DllOverride.Prefix == nil {
		t.Fatalf("record = %+v", record)
	}
	if _, err := Uninstall(game, nil); err != nil {
		t.Fatal(err)
	}
	if _, found := proton.ReadDllOverride(ppath.Normalize(prefix), proton.DLLName, ""); found {
		t.Error("the version.dll override survived uninstall")
	}
	entries, err := os.ReadDir(game)
	if err != nil {
		t.Fatal(err)
	}
	var names []string
	for _, entry := range entries {
		names = append(names, entry.Name())
	}
	if want := []string{"Megabonk.exe", "Megabonk_Data"}; !reflect.DeepEqual(names, want) {
		t.Errorf("game dir after uninstall = %v, want %v", names, want)
	}
}

func TestWineModeRepairsAWipedRuntimeAndItsOverrideTogether(t *testing.T) {
	packageDir, game, prefix := makePackage(t), makeGame(t), makePrefix(t)
	opts := wineOptions(game, prefix)
	built, err := BuildPlan(packageDir, opts)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := ApplyPlan(built, nil); err != nil {
		t.Fatal(err)
	}
	if err := os.RemoveAll(filepath.Join(game, "MelonLoader", "Dependencies", "dotnet")); err != nil {
		t.Fatal(err)
	}
	repair, err := BuildPlan(packageDir, opts)
	if err != nil {
		t.Fatal(err)
	}
	if got := kinds(repair.Actions); !reflect.DeepEqual(got, []string{"install-runtime", "enable-dll-override"}) {
		t.Errorf("repair = %v", got)
	}
}
