package modinstall

import (
	"path/filepath"
	"testing"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/content"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
	"github.com/pythoninthegrass/megabonk_mods/installer/internal/proton"
)

func TestOverrideOnlyRunSetsTheOverrideAndKeepsForeignFiles(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	dll := filepath.Join(gameDir, content.PluginsDir, content.ModFolderName, content.ModDLLName)
	writeFile(t, dll, "someone else's plugin")
	other := filepath.Join(gameDir, content.PluginsDir, "OtherMod", "Other.dll")
	writeFile(t, other, "another mod")

	result, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest}, OverrideOnly: true,
	}, nil)
	if err != nil {
		t.Fatal(err)
	}
	if !result.OverrideApplied {
		t.Errorf("override = %+v", result)
	}
	if !proton.WinHTTPOverrideApplied(prefix) {
		t.Error("the prefix has no winhttp override")
	}
	if !ppath.IsFile(dll) || !ppath.IsFile(other) {
		t.Error("an override-only run must not touch the loader or plugin files")
	}
	if ppath.IsFile(filepath.Join(gameDir, content.WinHTTPProxyName)) {
		t.Error("an override-only run must not install the loader")
	}
	record := content.LoadRecord(gameDir)
	if record == nil || record.DllOverride == nil || !record.DllOverride.Applied {
		t.Fatalf("record = %+v", record)
	}
	if record.Loader != nil {
		t.Errorf("an override-only run claims no loader install: %+v", record.Loader)
	}
	removed, err := Uninstall(gameDir, nil)
	if err != nil {
		t.Fatal(err)
	}
	if proton.WinHTTPOverrideApplied(prefix) {
		t.Error("the override survived the uninstall")
	}
	if !ppath.IsFile(dll) || !ppath.IsFile(other) {
		t.Error("the uninstall removed files it never placed")
	}
	if len(removed) != 0 {
		t.Errorf("removed = %v, want nothing but the prefix edit", removed)
	}
}

func TestOverrideOnlyRunUnderProtonGivesTheLaunchOption(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), protonPrefix(t)
	reported := &recorder{cancelAfter: -1}
	result, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformProton,
		Pins: map[string]string{bepinexVersion: stub.packDigest}, OverrideOnly: true,
	}, reported)
	if err != nil {
		t.Fatal(err)
	}
	if result.LaunchOption != proton.WinHTTPLaunchOption || !reported.launchOptionShown {
		t.Errorf("result = %+v, shown = %v", result, reported.launchOptionShown)
	}
	if _, found := proton.ReadDllOverride(prefix, proton.WinHTTPDLLName, ""); found {
		t.Error("a Proton prefix must not be edited behind Steam's back")
	}
}

func TestOverrideOnlyRecordSurvivesAForeignUninstall(t *testing.T) {
	stub := newStub(t)
	gameDir, prefix := vanillaGame(t), winePrefix(t)
	if _, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest}, OverrideOnly: true,
	}, nil); err != nil {
		t.Fatal(err)
	}
	if content.LoadRecord(gameDir) == nil {
		t.Fatal("the override run wrote no record")
	}
	// A foreign mod manager removes the plugin set; the record is still ours.
	dll := filepath.Join(gameDir, content.PluginsDir, content.ModFolderName, content.ModDLLName)
	writeFile(t, dll, "someone else's plugin")
	if _, err := Install(stub.client(), Options{
		Game: gameDir, Prefix: prefix, Platform: PlatformWine,
		Pins: map[string]string{bepinexVersion: stub.packDigest}, OverrideOnly: true,
	}, nil); err != nil {
		t.Fatal(err)
	}
	if !proton.WinHTTPOverrideApplied(prefix) {
		t.Fatal("the override was never applied")
	}
	removed, err := Uninstall(gameDir, nil)
	if err != nil {
		t.Fatal(err)
	}
	if proton.WinHTTPOverrideApplied(prefix) {
		t.Error("the override survived the uninstall")
	}
	if len(removed) != 0 {
		t.Errorf("removed = %v", removed)
	}
	if !ppath.IsFile(dll) {
		t.Error("an unrecorded plugin was removed")
	}
}
