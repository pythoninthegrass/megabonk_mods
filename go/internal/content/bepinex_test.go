package content

import (
	"archive/zip"
	"bytes"
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"strings"
	"testing"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

func zipEntries(t *testing.T, name string, entries [][2]string) string {
	t.Helper()
	archive := filepath.Join(t.TempDir(), name)
	handle, err := os.Create(archive)
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
	return archive
}

// packArchive is a loader pack archive in the shape Thunderstore serves it: the
// core assemblies, the winhttp proxy and doorstop configuration a manager
// installs, and the dotnet/ tree, .doorstop_version and changelog.txt its Apply
// leaves out.
func packArchive(t *testing.T) string {
	t.Helper()
	return zipEntries(t, "BepInExPack.zip", [][2]string{
		{"BepInExPack/doorstop_config.ini", "[UnityDoorstop]"},
		{"BepInExPack/winhttp.dll", "winhttp proxy"},
		{"BepInExPack/BepInEx/core/BepInEx.dll", "core"},
		{"BepInExPack/BepInEx/core/BepInEx.Unity.IL2CPP.dll", "il2cpp core"},
		{"BepInExPack/BepInEx/core/0Harmony.dll", "harmony"},
		{"BepInExPack/BepInEx/core/UnhollowerBaseLib.dll", "unhollower"},
		{"BepInExPack/dotnet/coreclr.dll", "coreclr"},
		{"BepInExPack/dotnet/host/fxr/6.0.36/hostfxr.dll", "hostfxr"},
		{"BepInExPack/dotnet/shared/Microsoft.NETCore.App/6.0.36/System.Private.CoreLib.dll", "corelib"},
		{"BepInExPack/.doorstop_version", "3.5.2"},
		{"BepInExPack/changelog.txt", "6.0.788"},
	})
}

func modArchive(t *testing.T) string {
	t.Helper()
	return zipEntries(t, "Megabonk_Level_Editor.zip", [][2]string{
		{"manifest.json", "{}"},
		{"README.md", "readme"},
		{"icon.png", "icon"},
		{"BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll", "mod dll"},
		{"BepInEx/plugins/MegabonkLevels/NLayer.dll", "nlayer"},
		{"BepInEx/plugins/MegabonkLevels/NLayer.LICENSE.txt", "license"},
	})
}

// gameDir is a Windows Megabonk folder: the installer refuses a directory that
// does not look like the build the loader hooks.
func gameDir(t *testing.T) string {
	t.Helper()
	game := t.TempDir()
	writeBytes(t, filepath.Join(game, "Megabonk.exe"), []byte("MZ"))
	if err := os.MkdirAll(filepath.Join(game, "Megabonk_Data"), 0o755); err != nil {
		t.Fatal(err)
	}
	return game
}

// melonLoaderGame is a Windows Megabonk folder left behind by a MelonLoader
// install: its version.dll proxy beside the executable.
func melonLoaderGame(t *testing.T) string {
	t.Helper()
	game := gameDir(t)
	writeBytes(t, filepath.Join(game, VersionDLLName), []byte("melan loader proxy"))
	if err := os.MkdirAll(filepath.Join(game, LoaderDir, "net6"), 0o755); err != nil {
		t.Fatal(err)
	}
	return game
}

// installedGame is a Windows Megabonk folder with the loader pack already in
// place: the mod archive is only installed into a folder that has a loader.
func installedGame(t *testing.T) string {
	t.Helper()
	game := gameDir(t)
	if _, err := InstallBepInEx(game, packArchive(t), "6.0.788"); err != nil {
		t.Fatal(err)
	}
	return game
}

// packFilesOf reads back the pack files sitting in a game folder, which is what
// a record has to name for uninstall to take the pack back.
func packFilesOf(t *testing.T, game string) []string {
	t.Helper()
	var names []string
	for _, name := range []string{DoorstopConfigName, WinHTTPProxyName, DoorstopVersionName, ChangelogName} {
		if ppathIsFile(filepath.Join(game, filepath.FromSlash(name))) {
			names = append(names, name)
		}
	}
	filepath.Walk(filepath.Join(game, "dotnet"), func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return err
		}
		relative, relErr := filepath.Rel(game, path)
		if relErr != nil {
			return relErr
		}
		names = append(names, filepath.ToSlash(relative))
		return nil
	})
	return names
}

func modFile(game string) string {
	return ppath.Join(game, BepInExDir, PluginsDir, ModFolderName, ModDLLName)
}

func TestInstallBepInExPlacesTheWholePackTree(t *testing.T) {
	game := gameDir(t)
	result, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err != nil {
		t.Fatal(err)
	}
	if result.Version != "6.0.788" || result.Placed == nil {
		t.Errorf("result = %+v", result)
	}
	for _, name := range []string{
		"doorstop_config.ini", "winhttp.dll",
		"BepInEx/core/BepInEx.dll", "BepInEx/core/BepInEx.Unity.IL2CPP.dll",
		"BepInEx/core/0Harmony.dll",
		"dotnet/coreclr.dll", "dotnet/host/fxr/6.0.36/hostfxr.dll",
		"dotnet/shared/Microsoft.NETCore.App/6.0.36/System.Private.CoreLib.dll",
		".doorstop_version", "changelog.txt",
	} {
		if !ppathIsFile(filepath.Join(game, filepath.FromSlash(name))) {
			t.Errorf("%s was not installed", name)
		}
	}
	if want := []string{
		".doorstop_version", "BepInEx/core/0Harmony.dll", "BepInEx/core/BepInEx.Unity.IL2CPP.dll",
		"BepInEx/core/BepInEx.dll", "BepInEx/core/UnhollowerBaseLib.dll",
		"changelog.txt", "doorstop_config.ini",
		"dotnet/coreclr.dll", "dotnet/host/fxr/6.0.36/hostfxr.dll",
		"dotnet/shared/Microsoft.NETCore.App/6.0.36/System.Private.CoreLib.dll", "winhttp.dll",
	}; !reflect.DeepEqual(result.PackFiles, want) {
		t.Errorf("pack files = %v, want %v", result.PackFiles, want)
	}
	if result.Parked {
		t.Error("nothing was parked in a directory with no version.dll")
	}
}

func TestInstallBepInExReportsWhatItPlaced(t *testing.T) {
	game := gameDir(t)
	first, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err != nil {
		t.Fatal(err)
	}
	if len(first.Placed) == 0 {
		t.Fatal("the first install placed nothing")
	}
	again, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err != nil {
		t.Fatal(err)
	}
	if again.Placed == nil {
		t.Errorf("a second install placed %v, want an empty list", again.Placed)
	}
	if len(again.Placed) != 0 || again.Version != "6.0.788" {
		t.Errorf("a second install placed %v", again.Placed)
	}
	writeBytes(t, filepath.Join(game, "dotnet", "coreclr.dll"), []byte("corrupted"))
	os.Remove(filepath.Join(game, "changelog.txt"))
	drift, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err != nil {
		t.Fatal(err)
	}
	if want := []string{"changelog.txt", "dotnet/coreclr.dll"}; !reflect.DeepEqual(drift.Placed, want) {
		t.Errorf("repair placed %v, want %v", drift.Placed, want)
	}
	body, err := os.ReadFile(filepath.Join(game, "dotnet", "coreclr.dll"))
	if err != nil || string(body) != "coreclr" {
		t.Errorf("the tampered file = %q, %v", body, err)
	}
}

func TestInstallBepInExRefusesAPackWithoutItsRuntime(t *testing.T) {
	game := gameDir(t)
	archive := zipEntries(t, "BepInExPack.zip", [][2]string{
		{"BepInExPack/winhttp.dll", "winhttp proxy"},
		{"BepInExPack/BepInEx/core/BepInEx.dll", "core"},
		{"BepInExPack/BepInEx/core/BepInEx.Unity.IL2CPP.dll", "il2cpp core"},
		{"BepInExPack/doorstop_config.ini", "[UnityDoorstop]"},
	})
	_, err := InstallBepInEx(game, archive, "6.0.788")
	if err == nil || !strings.Contains(err.Error(), "dotnet/coreclr.dll") {
		t.Errorf("a pack with no runtime = %v", err)
	}
	if ppath.IsDir(filepath.Join(game, "dotnet")) {
		t.Error("the refusal created dotnet/")
	}
}

func TestInstallBepInExRefusesAMissingPackFile(t *testing.T) {
	game := t.TempDir()
	_, err := InstallBepInEx(game, filepath.Join(t.TempDir(), "absent.zip"), "6.0.788")
	if err == nil {
		t.Fatal("a missing archive was accepted")
	}
}

func TestInstallBepInExRefusesAnEscapingEntry(t *testing.T) {
	game := gameDir(t)
	archive := zipEntries(t, "BepInExPack.zip", [][2]string{
		{"BepInExPack/winhttp.dll", "winhttp proxy"},
		{"BepInExPack/BepInEx/core/BepInEx.dll", "core"},
		{"BepInExPack/dotnet/coreclr.dll", "coreclr"},
		{"BepInExPack/.doorstop_version", "3.5.2"},
		{"BepInExPack/changelog.txt", "6.0.788"},
		{"BepInExPack/../../evil.dll", "MZ"},
	})
	if _, err := InstallBepInEx(game, archive, "6.0.788"); err == nil ||
		!strings.Contains(err.Error(), "escape") {
		t.Errorf("escaping entry = %v", err)
	}
	if ppath.Exists(filepath.Join(game, "..", "evil.dll")) {
		t.Error("the escaping entry was written")
	}
}

func TestInstallBepInExParksTheMelonLoaderProxy(t *testing.T) {
	game := melonLoaderGame(t)
	result, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err != nil {
		t.Fatal(err)
	}
	if !result.Parked {
		t.Errorf("the MelonLoader proxy was not parked: %+v", result)
	}
	if ppath.Exists(filepath.Join(game, VersionDLLName)) {
		t.Error("the MelonLoader proxy is still loaded by Wine")
	}
	body, err := os.ReadFile(filepath.Join(game, "version.dll.bak"))
	if err != nil || string(body) != "melan loader proxy" {
		t.Errorf("version.dll.bak = %q, %v", body, err)
	}
}

func TestInstallBepInExRefusesAnUnknownProxy(t *testing.T) {
	game := gameDir(t)
	writeBytes(t, filepath.Join(game, VersionDLLName), []byte("not a loader proxy"))
	_, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err == nil || !strings.Contains(err.Error(), "version.dll") {
		t.Errorf("an unknown version.dll = %v", err)
	}
	if !ppath.IsFile(filepath.Join(game, VersionDLLName)) {
		t.Error("the unknown proxy was moved out of the way")
	}
	if ppath.Exists(filepath.Join(game, "BepInEx")) {
		t.Error("the refusal still installed the loader")
	}
}

func TestInstallBepInExRefusesAnExistingBackup(t *testing.T) {
	game := melonLoaderGame(t)
	writeBytes(t, filepath.Join(game, ProxyBackupName), []byte("an earlier proxy"))
	_, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err == nil || !strings.Contains(err.Error(), ProxyBackupName) {
		t.Errorf("an existing backup = %v", err)
	}
	if !ppath.IsFile(filepath.Join(game, VersionDLLName)) {
		t.Error("the proxy was parked over the player's own backup")
	}
}

func TestUninstallBepInExTakesTheLoaderBack(t *testing.T) {
	game := gameDir(t)
	pack, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := InstallModFromZip(game, modArchive(t), "0.2.0"); err != nil {
		t.Fatal(err)
	}
	if err := WriteBepInExInstallRecord(game, "6.0.788", "0.2.0", pack.PackFiles, false); err != nil {
		t.Fatal(err)
	}
	record := LoadRecord(game)
	if record == nil {
		t.Fatal("no record was written")
	}

	removed, err := UninstallBepInEx(game, record)
	if err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"BepInEx", "dotnet", "changelog.txt", ".doorstop_version",
		ModDLLName, NLayerName, LicenseName, "winhttp.dll", "doorstop_config.ini"} {
		if ppath.Exists(filepath.Join(game, filepath.FromSlash(name))) {
			t.Errorf("%s survived the uninstall", name)
		}
	}
	if InstalledBepInExVersion(game) != "" || InstalledModVersion(game) != "" {
		t.Error("the versions still read as installed")
	}
	if ModInstalled(game) {
		t.Error("the mod still detects as installed")
	}
	// The pack's own winhttp.dll proxy was placed by this installer, so it goes
	// with the rest of the pack.
	for _, line := range removed {
		if strings.HasPrefix(line, "/") || strings.Contains(line, game) {
			t.Errorf("removed %q is an absolute path", line)
		}
	}
	if _, err := UninstallBepInEx(game, record); err != nil {
		t.Errorf("a second uninstall = %v", err)
	}
}

func TestUninstallBepInExRestoresTheParkedProxy(t *testing.T) {
	game := melonLoaderGame(t)
	pack, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := InstallModFromZip(game, modArchive(t), "0.2.0"); err != nil {
		t.Fatal(err)
	}
	if err := WriteBepInExInstallRecord(game, "6.0.788", "0.2.0", pack.PackFiles, true); err != nil {
		t.Fatal(err)
	}
	if _, err := UninstallBepInEx(game, LoadRecord(game)); err != nil {
		t.Fatal(err)
	}
	body, err := os.ReadFile(filepath.Join(game, VersionDLLName))
	if err != nil || string(body) != "melan loader proxy" {
		t.Errorf("version.dll = %q, %v", body, err)
	}
	if ppath.Exists(filepath.Join(game, ProxyBackupName)) {
		t.Error("the backup stayed behind after the restore")
	}
}

func TestUninstallBepInExLeavesWhatItDidNotPlace(t *testing.T) {
	game := gameDir(t)
	// A proxy the player parked by hand, and another mod's assembly sharing the
	// BepInEx folder the pack created.
	writeBytes(t, filepath.Join(game, ProxyBackupName), []byte("the player's own proxy"))
	if _, err := InstallBepInEx(game, packArchive(t), "6.0.788"); err != nil {
		t.Fatal(err)
	}
	writeBytes(t, filepath.Join(game, "BepInEx", "plugins", "Other", "Other.dll"), []byte("other mod"))
	if _, err := InstallModFromZip(game, modArchive(t), "0.2.0"); err != nil {
		t.Fatal(err)
	}
	if err := WriteBepInExInstallRecord(game, "6.0.788", "0.2.0", packFilesOf(t, game), false); err != nil {
		t.Fatal(err)
	}
	if _, err := UninstallBepInEx(game, LoadRecord(game)); err != nil {
		t.Fatal(err)
	}
	if !ppath.IsFile(filepath.Join(game, ProxyBackupName)) {
		t.Error("a backup the installer did not park was removed")
	}
	if ppath.Exists(filepath.Join(game, VersionDLLName)) {
		t.Error("the proxy was restored from a backup the installer did not park")
	}
	if !ppath.IsFile(filepath.Join(game, "BepInEx", "plugins", "Other", "Other.dll")) {
		t.Error("another mod's files were removed")
	}
	if ppath.IsFile(filepath.Join(game, "changelog.txt")) || ppath.IsDir(filepath.Join(game, "dotnet")) {
		t.Error("the pack files the installer placed survived")
	}
}

func TestUninstallBepInExKeepsALoaderStillInUse(t *testing.T) {
	game := gameDir(t)
	if _, err := InstallBepInEx(game, packArchive(t), "6.0.788"); err != nil {
		t.Fatal(err)
	}
	if _, err := InstallModFromZip(game, modArchive(t), "0.2.0"); err != nil {
		t.Fatal(err)
	}
	// Another mod manager's assemblies share the BepInEx folder the pack created.
	writeBytes(t, filepath.Join(game, "BepInEx", "core", "BepInEx.Unity.Mono.dll"), []byte("another loader"))
	if err := WriteBepInExInstallRecord(game, "6.0.788", "0.2.0", packFilesOf(t, game), false); err != nil {
		t.Fatal(err)
	}
	if _, err := UninstallBepInEx(game, LoadRecord(game)); err != nil {
		t.Fatal(err)
	}
	if !ppath.IsFile(filepath.Join(game, "BepInEx", "core", "BepInEx.Unity.Mono.dll")) {
		t.Error("a file the installer did not place was removed")
	}
	if !ppath.IsDir(filepath.Join(game, "BepInEx")) {
		t.Error("a BepInEx folder that is still in use was removed")
	}
	if ppath.IsFile(filepath.Join(game, "changelog.txt")) || ppath.IsDir(filepath.Join(game, "dotnet")) {
		t.Error("the pack files the installer placed survived")
	}
}

func TestUninstallBepInExRefusesToChooseBetweenTwoProxies(t *testing.T) {
	game := melonLoaderGame(t)
	pack, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := InstallModFromZip(game, modArchive(t), "0.2.0"); err != nil {
		t.Fatal(err)
	}
	if err := WriteBepInExInstallRecord(game, "6.0.788", "0.2.0", pack.PackFiles, true); err != nil {
		t.Fatal(err)
	}
	// A manager put a proxy back where the installer parked one.
	writeBytes(t, filepath.Join(game, VersionDLLName), []byte("someone else's proxy"))
	if _, err := UninstallBepInEx(game, LoadRecord(game)); err == nil ||
		!strings.Contains(err.Error(), VersionDLLName) {
		t.Errorf("two proxies in play = %v", err)
	}
	if !ppath.IsFile(filepath.Join(game, VersionDLLName)) {
		t.Error("a proxy the installer did not park was removed")
	}
	if !ppath.IsFile(filepath.Join(game, ProxyBackupName)) {
		t.Error("the parked proxy was dropped instead of kept for the player")
	}
}

func TestUninstallBepInExWithoutARecordRemovesNothing(t *testing.T) {
	game := installedGame(t)
	writeBytes(t, filepath.Join(game, PluginsDir, ModFolderName, ModDLLName), []byte("dll"))
	removed, err := UninstallBepInEx(game, nil)
	if err != nil {
		t.Fatal(err)
	}
	if len(removed) != 0 {
		t.Errorf("removed = %v, want nothing without a record", removed)
	}
	if !ppath.IsFile(filepath.Join(game, "changelog.txt")) || !ppath.IsDir(filepath.Join(game, "dotnet")) {
		t.Error("an unrecorded loader pack was torn out")
	}
}

func TestInstallModFromZipMergesTheBepInExTree(t *testing.T) {
	game := gameDir(t)
	if _, err := InstallBepInEx(game, packArchive(t), "6.0.788"); err != nil {
		t.Fatal(err)
	}
	// An earlier install of the mod is what Replaced reports.
	if _, err := InstallModFromZip(game, modArchive(t), "0.1.9"); err != nil {
		t.Fatal(err)
	}
	result, err := InstallModFromZip(game, modArchive(t), "0.2.0")
	if err != nil {
		t.Fatal(err)
	}
	if result.Version != "0.2.0" {
		t.Errorf("version = %q", result.Version)
	}
	if !result.Replaced {
		t.Error("nothing had been replaced")
	}
	want := []string{
		"BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll",
		"BepInEx/plugins/MegabonkLevels/NLayer.LICENSE.txt",
		"BepInEx/plugins/MegabonkLevels/NLayer.dll",
	}
	if !reflect.DeepEqual(result.Files, want) {
		t.Errorf("files = %v, want %v", result.Files, want)
	}
	for _, name := range []string{"winhttp.dll", "changelog.txt", "BepInEx/core/BepInEx.dll"} {
		if !ppath.IsFile(filepath.Join(game, filepath.FromSlash(name))) {
			t.Errorf("the merge removed %s", name)
		}
	}
}

func TestInstallModFromZipRepairsAndReplaces(t *testing.T) {
	game := gameDir(t)
	if _, err := InstallBepInEx(game, packArchive(t), "6.0.788"); err != nil {
		t.Fatal(err)
	}
	writeBytes(t, filepath.Join(game, "BepInEx", "plugins", "MegabonkLevels", ModDLLName), []byte("stale build"))
	result, err := InstallModFromZip(game, modArchive(t), "0.2.0")
	if err != nil {
		t.Fatal(err)
	}
	if !result.Replaced {
		t.Error("the stale plugin file was not reported as replaced")
	}
	body, err := os.ReadFile(filepath.Join(game, "BepInEx", "plugins", "MegabonkLevels", ModDLLName))
	if err != nil || string(body) != "mod dll" {
		t.Errorf("the plugin file = %q, %v", body, err)
	}
}

func TestInstallModFromZipRefusesTheWrongArchive(t *testing.T) {
	for _, test := range []struct {
		name    string
		entries [][2]string
		want    string
	}{
		{"a loader pack is not the mod", [][2]string{{"BepInExPack/winhttp.dll", "proxy"}}, "BepInEx/plugins/MegabonkLevels"},
		{"no plugin folder at all", [][2]string{{"BepInEx/other/x.dll", "dll"}}, "BepInEx/plugins/MegabonkLevels"},
		{"an empty plugin folder", [][2]string{
			{"BepInEx/plugins/MegabonkLevels/", ""},
			{"BepInEx/plugins/MegabonkLevels/sub/", ""},
		}, "BepInEx/plugins/MegabonkLevels"},
		{"no NLayer", [][2]string{{"BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll", "dll"}}, NLayerName},
		{"no license", [][2]string{
			{"BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll", "dll"},
			{"BepInEx/plugins/MegabonkLevels/NLayer.dll", "dll"},
		}, LicenseName},
		{"only the icon", [][2]string{{"icon.png", "icon"}, {"README.md", "readme"}},
			"BepInEx/plugins/MegabonkLevels"},
	} {
		t.Run(test.name, func(t *testing.T) {
			game := installedGame(t)
			archive := zipEntries(t, "mod.zip", test.entries)
			_, err := InstallModFromZip(game, archive, "0.2.0")
			if err == nil || !strings.Contains(err.Error(), test.want) {
				t.Errorf("err = %v, want one naming %s", err, test.want)
			}
			if ppath.Exists(filepath.Join(game, "BepInEx", "plugins", "MegabonkLevels", ModDLLName)) {
				t.Error("a refused archive still placed the plugin")
			}
		})
	}
}

func TestInstallModFromZipRefusesAnEscapingEntry(t *testing.T) {
	game := installedGame(t)
	archive := zipEntries(t, "mod.zip", [][2]string{
		{"BepInEx/plugins/MegabonkLevels/MegabonkLevels.Mod.dll", "dll"},
		{"BepInEx/plugins/MegabonkLevels/NLayer.dll", "dll"},
		{"BepInEx/plugins/MegabonkLevels/NLayer.LICENSE.txt", "license"},
		{"BepInEx/plugins/MegabonkLevels/../../../evil.dll", "MZ"},
	})
	if _, err := InstallModFromZip(game, archive, "0.2.0"); err == nil ||
		!strings.Contains(err.Error(), "escape") {
		t.Errorf("escaping entry = %v", err)
	}
	if ppath.Exists(filepath.Join(game, "..", "evil.dll")) {
		t.Error("the escaping entry was written")
	}
}

func TestModDetectionNeedsThePluginFileAndTheRecord(t *testing.T) {
	game := t.TempDir()
	if ModInstalled(game) {
		t.Fatal("a vanilla directory has no mod")
	}
	if got := InstalledModVersion(game); got != "" {
		t.Errorf("InstalledModVersion = %q", got)
	}
	// A manager's files are there for the player to see, but nothing recorded
	// them, so only ModInstalled says yes: the checkbox follows the files, the
	// installer's own claims follow the record.
	writeBytes(t, filepath.Join(game, "BepInEx", "plugins", "MegabonkLevels", ModDLLName), []byte("dll"))
	writeBytes(t, filepath.Join(game, "BepInEx", "plugins", "MegabonkLevels", NLayerName), []byte("dll"))
	writeBytes(t, filepath.Join(game, "BepInEx", "plugins", "MegabonkLevels", LicenseName), []byte("license"))
	if !ModInstalled(game) {
		t.Error("the files the loader reads are what the checkbox reports")
	}
	if got := InstalledModVersion(game); got != "" {
		t.Errorf("InstalledModVersion without a record = %q", got)
	}
	// A record that does not say the installer installed the loader is not either.
	path, err := SaveRecord(game, &Record{Schema: RecordSchema, ModVersion: "0.2.0", BepinexVersion: "6.0.788"})
	if err != nil {
		t.Fatal(err)
	}
	if !ModInstalled(game) {
		t.Error("the plugin files are still there, so the checkbox still says installed")
	}
	if err := os.Remove(path); err != nil {
		t.Fatal(err)
	}
	// A stray file under BepInEx is not what makes an install detectable.
	writeBytes(t, filepath.Join(game, "BepInEx", "plugins", "Other", "Other.dll"), []byte("other"))
	if err := os.Remove(filepath.Join(game, "BepInEx", "plugins", "Other", "Other.dll")); err != nil {
		t.Fatal(err)
	}
	// A folder that is not the mod's own does not make this mod installed.
	if err := os.Remove(filepath.Join(game, "BepInEx", "plugins", "MegabonkLevels", ModDLLName)); err != nil {
		t.Fatal(err)
	}
	if ModInstalled(game) {
		t.Error("an incomplete plugin folder is not an install")
	}
	writeBytes(t, filepath.Join(game, "BepInEx", "plugins", "MegabonkLevels", ModDLLName), []byte("dll"))
	pack, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err != nil {
		t.Fatal(err)
	}
	if err := WriteBepInExInstallRecord(game, "6.0.788", "0.2.0", pack.PackFiles, false); err != nil {
		t.Fatal(err)
	}
	if !ModInstalled(game) {
		t.Error("the plugin files and a record should read as installed")
	}
	if got := InstalledModVersion(game); got != "0.2.0" {
		t.Errorf("InstalledModVersion = %q", got)
	}
	if got := InstalledBepInExVersion(game); got != "6.0.788" {
		t.Errorf("InstalledBepInExVersion = %q", got)
	}
}

func TestModDetectionNeedsEveryRecordedFile(t *testing.T) {
	game := gameDir(t)
	pack, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := InstallModFromZip(game, modArchive(t), "0.2.0"); err != nil {
		t.Fatal(err)
	}
	if err := WriteBepInExInstallRecord(game, "6.0.788", "0.2.0", pack.PackFiles, false); err != nil {
		t.Fatal(err)
	}
	if !ModInstalled(game) {
		t.Fatal("a complete install should read as installed")
	}
	// The player disables the mod the way the package README says: park the folder.
	if err := os.Rename(filepath.Join(game, "BepInEx", "plugins", ModFolderName),
		filepath.Join(game, "BepInEx", "plugins", "MegabonkLevels.disabled")); err != nil {
		t.Fatal(err)
	}
	if ModInstalled(game) {
		t.Error("a parked plugin folder is not installed")
	}
}

func TestInstallRecordsTheLoaderAndModVersions(t *testing.T) {
	game := gameDir(t)
	writeBytes(t, filepath.Join(game, VersionDLLName), []byte("melan loader proxy"))
	if err := os.MkdirAll(filepath.Join(game, LoaderDir, "net6"), 0o755); err != nil {
		t.Fatal(err)
	}
	parked, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err != nil {
		t.Fatal(err)
	}
	if !parked.Parked {
		t.Fatal("the MelonLoader proxy was not parked")
	}

	if _, err := InstallModFromZip(game, modArchive(t), "0.2.0"); err != nil {
		t.Fatal(err)
	}
	if err := WriteBepInExInstallRecord(game, "6.0.788", "0.2.0", parked.PackFiles, parked.Parked); err != nil {
		t.Fatal(err)
	}
	loaded := LoadRecord(game)
	if loaded == nil {
		t.Fatal("no record")
	}
	if loaded.BepinexVersion != "6.0.788" || loaded.ModVersion != "0.2.0" {
		t.Errorf("versions = %q / %q", loaded.BepinexVersion, loaded.ModVersion)
	}
	if loaded.Loader == nil || loaded.Loader.BepInExVersion != "6.0.788" ||
		loaded.Loader.ModVersion != "0.2.0" || !loaded.Loader.ProxyParked {
		t.Errorf("loader = %+v", loaded.Loader)
	}
	again, err := DetectLoader(game)
	if err != nil {
		t.Fatal(err)
	}
	if again == nil || !again.Installed || !again.ProxyParked ||
		again.ProxyBackup == nil || *again.ProxyBackup != ProxyBackupName {
		t.Errorf("DetectLoader = %+v", again)
	}
	if !ModInstalled(game) {
		t.Error("the recorded install should detect as installed")
	}
}

func TestSaveBepInExRecordWritesTheVersionsIntoTheRecord(t *testing.T) {
	game := gameDir(t)
	pack, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := InstallModFromZip(game, modArchive(t), "0.2.0"); err != nil {
		t.Fatal(err)
	}
	state, err := BepInExInstallRecord("6.0.788", "0.2.0", pack.PackFiles, false)
	if err != nil {
		t.Fatal(err)
	}
	record := &Record{Schema: RecordSchema, GameDir: ppath.Normalize(game), Loader: state}
	if err := SaveBepInExRecord(game, record); err != nil {
		t.Fatal(err)
	}
	loaded := LoadRecord(game)
	if loaded == nil {
		t.Fatal("no record was written")
	}
	if loaded.BepinexVersion != "6.0.788" || loaded.ModVersion != "0.2.0" {
		t.Errorf("record versions = %q / %q", loaded.BepinexVersion, loaded.ModVersion)
	}
	if loaded.Loader == nil || !loaded.Loader.Installed {
		t.Errorf("loader = %+v", loaded.Loader)
	}
	if _, err := UninstallBepInEx(game, loaded); err != nil {
		t.Fatal(err)
	}
	if ppath.Exists(filepath.Join(game, "changelog.txt")) {
		t.Error("the uninstall did not take the pack back")
	}
}

func TestSaveBepInExRecordRefusesAnEmptyLoader(t *testing.T) {
	game := gameDir(t)
	if err := SaveBepInExRecord(game, &Record{Schema: RecordSchema}); err == nil {
		t.Error("a record with no loader entry was written")
	}
	if _, err := BepInExInstallRecord("", "0.2.0", []string{ChangelogName}, false); err == nil {
		t.Error("a loader entry with no pack version was accepted")
	}
	if _, err := BepInExInstallRecord("6.0.788", "", []string{ChangelogName}, false); err == nil {
		t.Error("a loader entry with no mod version was accepted")
	}
	if _, err := BepInExInstallRecord("6.0.788", "0.2.0", nil, false); err == nil {
		t.Error("a loader entry naming no pack file was accepted")
	}
	if _, err := BepInExInstallRecord("6.0.788", "0.2.0", []string{"UserData/Levels/mine.mblevel.json"}, false); err == nil {
		t.Error("a player file was accepted as a pack file")
	}
}

func TestDetectLoaderReadsOnlyWhatWasRecorded(t *testing.T) {
	game := gameDir(t)
	pack, err := InstallBepInEx(game, packArchive(t), "6.0.788")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := InstallModFromZip(game, modArchive(t), "0.2.0"); err != nil {
		t.Fatal(err)
	}
	if err := WriteBepInExInstallRecord(game, "6.0.788", "0.2.0", pack.PackFiles, false); err != nil {
		t.Fatal(err)
	}
	state, err := DetectLoader(game)
	if err != nil || state == nil {
		t.Fatalf("DetectLoader = %+v, %v", state, err)
	}
	if state.BepInExVersion != "6.0.788" || state.ModVersion != "0.2.0" {
		t.Errorf("state = %+v", state)
	}
	// A record written before the loader entry existed still loads, and detects
	// nothing: the installer cannot know what a manager installed.
	writeBytes(t, filepath.Join(game, RecordName), []byte(`{"schema":"megabonk-levels-install/2","mod_version":"0.1.0"}`))
	if state, err := DetectLoader(game); err != nil || state != nil {
		t.Errorf("DetectLoader over a loader-less record = %+v, %v", state, err)
	}
	if err := os.Remove(RecordFilePath(game)); err != nil {
		t.Fatal(err)
	}
	if state, err := DetectLoader(game); err != nil || state != nil {
		t.Errorf("DetectLoader with no record = %+v, %v", state, err)
	}
}

func TestBepInExInstallUninstallIsIdempotent(t *testing.T) {
	game := melonLoaderGame(t)
	keep := []byte("melan loader proxy")
	for round := 0; round < 2; round++ {
		pack, err := InstallBepInEx(game, packArchive(t), "6.0.788")
		if err != nil {
			t.Fatal(err)
		}
		if _, err := InstallModFromZip(game, modArchive(t), "0.2.0"); err != nil {
			t.Fatal(err)
		}
		if err := WriteBepInExInstallRecord(game, "6.0.788", "0.2.0", pack.PackFiles, true); err != nil {
			t.Fatal(err)
		}
		if _, err := UninstallBepInEx(game, LoadRecord(game)); err != nil {
			t.Fatal(err)
		}
		entries, err := os.ReadDir(game)
		if err != nil {
			t.Fatal(err)
		}
		names := []string{}
		for _, entry := range entries {
			names = append(names, entry.Name())
		}
		want := []string{VersionDLLName, "MelonLoader", "Megabonk.exe", "Megabonk_Data", RecordName}
		sort.Strings(names)
		sort.Strings(want)
		if !reflect.DeepEqual(names, want) {
			t.Fatalf("round %d left %v, want %v", round, names, want)
		}
		body, err := os.ReadFile(filepath.Join(game, VersionDLLName))
		if err != nil || !bytes.Equal(body, keep) {
			t.Fatalf("round %d left the player with version.dll = %q, %v", round, body, err)
		}
	}
}

// The loader state has to survive the trip to disk and back, because a repair or
// an uninstall reads nothing else: it has to know which pack files to remove,
// whether the proxy is the one it parked, and which digest proved the archive it
// is being asked to reuse from the cache.
func TestLoaderRecordSurvivesADiskRoundTrip(t *testing.T) {
	game := gameDir(t)
	prefix := "prefix"
	via := "wine"
	backup := ProxyBackupName
	saved := &Record{
		Schema:         RecordSchema,
		ModVersion:     "0.2.0",
		BepinexVersion: "6.0.788",
		Loader: &LoaderState{
			BepInExVersion: "6.0.788",
			ModVersion:     "0.2.0",
			Installed:      true,
			PackFiles:      []string{"winhttp.dll", "doorstop_config.ini", "dotnet/coreclr.dll"},
			ProxyParked:    true,
			ProxyBackup:    &backup,
			ModSHA256:      strings.Repeat("a", 64),
		},
		DllOverride: &DllOverride{
			Applied: true, Name: "winhttp", Value: "native,builtin", Via: &via, Prefix: &prefix,
		},
	}
	if _, err := SaveRecord(game, saved); err != nil {
		t.Fatal(err)
	}
	got := LoadRecord(game)
	if got == nil || got.Loader == nil {
		t.Fatalf("the loader state did not survive: %+v", got)
	}
	want := *saved.Loader
	gotState := *got.Loader
	if gotState.BepInExVersion != want.BepInExVersion || gotState.ModVersion != want.ModVersion ||
		gotState.Installed != want.Installed || gotState.ProxyParked != want.ProxyParked ||
		gotState.ModSHA256 != want.ModSHA256 ||
		(gotState.ProxyBackup == nil) != (want.ProxyBackup == nil) ||
		(gotState.ProxyBackup != nil && *gotState.ProxyBackup != *want.ProxyBackup) ||
		strings.Join(gotState.PackFiles, "|") != strings.Join(want.PackFiles, "|") {
		t.Errorf("the loader state came back as %+v, want %+v", gotState, want)
	}
	if got.DllOverride == nil || got.DllOverride.Prefix == nil || *got.DllOverride.Prefix != prefix {
		t.Errorf("the override did not survive: %+v", got.DllOverride)
	}
	// A record with no loader half is not a loader install, and reads as one.
	plain := &Record{Schema: RecordSchema, ModVersion: "0.2.0"}
	other := gameDir(t)
	if _, err := SaveRecord(other, plain); err != nil {
		t.Fatal(err)
	}
	if loaded := LoadRecord(other); loaded.Loader != nil {
		t.Errorf("a record with no loader half read as one: %+v", loaded.Loader)
	}
}
