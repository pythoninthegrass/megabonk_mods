package proton

import (
	"archive/zip"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"

	"github.com/pythoninthegrass/megabonk_mods/installer/internal/ppath"
)

func write(t *testing.T, path, text string) string {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(text), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func prefixDir(t *testing.T) string {
	t.Helper()
	prefix := filepath.Join(t.TempDir(), "compatdata", "3405340", "pfx")
	if err := os.MkdirAll(filepath.Join(prefix, "drive_c"), 0o755); err != nil {
		t.Fatal(err)
	}
	return prefix
}

func TestWindowsPathMapsOntoTheWineZDrive(t *testing.T) {
	got := WindowsPath("/media/sdcard/SteamLibrary/steamapps/common/Megabonk/dotnet6-win")
	want := `Z:\media\sdcard\SteamLibrary\steamapps\common\Megabonk\dotnet6-win`
	if got != want {
		t.Errorf("WindowsPath = %q, want %q", got, want)
	}
	if got := WindowsPath(`C:\games\dotnet`); got != `C:\games\dotnet` {
		t.Errorf("an existing drive letter should survive: %q", got)
	}
	if got := WindowsPath(`c:/games/dotnet`); got != `C:\games\dotnet` {
		t.Errorf("a lowercase drive should be upper-cased: %q", got)
	}
}

func TestRuntimeTargetIsTheStandardDotnetFolder(t *testing.T) {
	prefix := prefixDir(t)
	if got := RuntimeTarget(prefix); got != filepath.ToSlash(prefix)+"/drive_c/Program Files/dotnet" {
		t.Errorf("RuntimeTarget = %q", got)
	}
}

func TestRuntimeInstalledNeedsTheMarkerAndHostfxr(t *testing.T) {
	target := RuntimeTarget(prefixDir(t))
	if RuntimeInstalled(target, "6.0.36") {
		t.Fatal("an empty target is not installed")
	}
	write(t, filepath.Join(target, "host", "fxr", "6.0.36", "hostfxr.dll"), "MZ")
	if RuntimeInstalled(target, "6.0.36") {
		t.Fatal("the marker has to say so too")
	}
	write(t, filepath.Join(target, RuntimeMarkerName), " 6.0.36 \n")
	if !RuntimeInstalled(target, "6.0.36") {
		t.Fatal("marker plus hostfxr is installed")
	}
	if RuntimeInstalled(target, "6.0.30") {
		t.Fatal("a different version is not installed")
	}
}

func writeZip(t *testing.T, entries map[string]string) string {
	t.Helper()
	archive := filepath.Join(t.TempDir(), "dotnet.zip")
	handle, err := os.Create(archive)
	if err != nil {
		t.Fatal(err)
	}
	zipWriter := zip.NewWriter(handle)
	for name, body := range entries {
		member, err := zipWriter.Create(name)
		if err != nil {
			t.Fatal(err)
		}
		if _, err := member.Write([]byte(body)); err != nil {
			t.Fatal(err)
		}
	}
	if err := zipWriter.Close(); err != nil {
		t.Fatal(err)
	}
	if err := handle.Close(); err != nil {
		t.Fatal(err)
	}
	return archive
}

func TestExtractRuntimeLaysOutDotnetAndWritesTheMarker(t *testing.T) {
	archive := writeZip(t, map[string]string{
		"dotnet.exe":                  "MZ",
		"host/fxr/6.0.36/hostfxr.dll": "MZ",
		"shared/Microsoft.NETCore.App/6.0.36/System.dll": "MZ",
	})
	target := RuntimeTarget(prefixDir(t))
	if err := ExtractRuntime(archive, target, "6.0.36"); err != nil {
		t.Fatal(err)
	}
	for _, name := range []string{"dotnet.exe", "host/fxr/6.0.36/hostfxr.dll", "shared/Microsoft.NETCore.App/6.0.36/System.dll"} {
		if !ppath.IsFile(ppath.Join(target, name)) {
			t.Errorf("%s was not extracted", name)
		}
	}
	if !RuntimeInstalled(target, "6.0.36") {
		t.Error("the runtime should read as installed")
	}
	marker, err := os.ReadFile(filepath.Join(target, RuntimeMarkerName))
	if err != nil || string(marker) != "6.0.36" {
		t.Errorf("marker = %q, %v", marker, err)
	}
}

func TestExtractRuntimeRejectsAnEscapingEntry(t *testing.T) {
	archive := writeZip(t, map[string]string{"../../escaped.dll": "MZ"})
	target := RuntimeTarget(prefixDir(t))
	err := ExtractRuntime(archive, target, "6.0.36")
	if err == nil {
		t.Fatal("an entry that climbs out of the target must be refused")
	}
	if !strings.Contains(err.Error(), "would escape its target directory") || !strings.Contains(err.Error(), "escaped.dll") {
		t.Errorf("err = %v", err)
	}
	if _, statErr := os.Stat(filepath.Join(target, "..", "..", "escaped.dll")); statErr == nil {
		t.Error("the escaping entry was written anyway")
	}

	archive = writeZip(t, map[string]string{"/etc/escaped.dll": "MZ"})
	if err := ExtractRuntime(archive, target, "6.0.36"); err == nil ||
		!strings.Contains(err.Error(), "would escape its target directory") {
		t.Errorf("an absolute entry should be refused too, got %v", err)
	}
}

const wineUserReg = `WINE REGISTRY Version 2
;; All keys relative to REGISTRY\User\S-1-5-21-1
` + "\n" + `#arch=win64

[Software\\Wine\\AppDefaults\\ffxvi.exe\\DllOverrides] 1793463286
"#time=1dd6952f286302a"
"atiadlxx"="builtin"

[Software\\Wine\\DllOverrides] 1793463301
"#time=1dd6952fb51ad38"
"api-ms-win-crt-heap-l1-1-0"="native,builtin"
"version"="native,builtin"

[Software\\Wine\\Fonts] 1793463286
"#time=1dd6952f285031c"
'@=""
`

func TestReadDllOverrideReadsWhatWineWrote(t *testing.T) {
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), wineUserReg)
	if got, ok := ReadDllOverride(prefix, "version", ""); !ok || got != "native,builtin" {
		t.Errorf("version = %q, %v", got, ok)
	}
	if got, ok := ReadDllOverride(prefix, "VERSION", ""); !ok || got != "native,builtin" {
		t.Errorf("the name should be case-insensitive: %q, %v", got, ok)
	}
	if _, ok := ReadDllOverride(prefix, "atiadlxx", ""); ok {
		t.Error("an AppDefaults section is not the game's DllOverrides")
	}
	if _, ok := ReadDllOverride(prefix, "nope", ""); ok {
		t.Error("an unknown name has no value")
	}

	missing := prefixDir(t)
	if _, ok := ReadDllOverride(missing, "version", ""); ok {
		t.Error("a prefix with no user.reg has no override")
	}
	write(t, filepath.Join(missing, "user.reg"), `REGEDIT4

[Software\\Wine\\AppDefaults]
"foo"="bar"
`)
	if _, ok := ReadDllOverride(missing, "version", ""); ok {
		t.Error("no DllOverrides section means no override")
	}
}

func TestSetDllOverrideCreatesTheSectionAndEntry(t *testing.T) {
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), "REGEDIT4\n\n[Software\\\\Wine\\\\AppDefaults]\n\"foo\"=\"bar\"\n")
	if got := SetDllOverride(prefix, DLLName, DLLValue, "", "", nil); got != "registry" {
		t.Fatalf("via = %q", got)
	}
	text, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	body := string(text)
	if !strings.Contains(body, `[Software\Wine\DllOverrides]`) {
		t.Errorf("the section is missing:\n%s", body)
	}
	if !strings.Contains(body, `"foo"="bar"`) {
		t.Errorf("the other section was lost:\n%s", body)
	}
	if got, ok := ReadDllOverride(prefix, DLLName, ""); !ok || got != DLLValue {
		t.Errorf("round trip = %q, %v", got, ok)
	}
}

func TestSetDllOverrideReplacesWithoutDuplicating(t *testing.T) {
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), "REGEDIT4\n\n[Software\\\\Wine\\\\DllOverrides]\n\"version\"=\"builtin\"\n")
	SetDllOverride(prefix, DLLName, DLLValue, "", "", nil)
	SetDllOverride(prefix, DLLName, DLLValue, "", "", nil)
	text, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	if count := strings.Count(string(text), `"version"=`); count != 1 {
		t.Errorf("the entry appears %d times:\n%s", count, text)
	}
	if got, ok := ReadDllOverride(prefix, DLLName, ""); !ok || got != DLLValue {
		t.Errorf("value = %q, %v", got, ok)
	}
}

func TestSetDllOverrideEditsARealWineFileInPlace(t *testing.T) {
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), strings.Replace(wineUserReg, "\n\"version\"=\"native,builtin\"", "", 1))
	if got := SetDllOverride(prefix, DLLName, DLLValue, "", "", nil); got != "registry" {
		t.Fatalf("via = %q", got)
	}
	text, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	body := string(text)
	if count := strings.Count(body, `[Software\\Wine\\DllOverrides]`); count != 1 {
		t.Errorf("the section appears %d times:\n%s", count, body)
	}
	start := strings.Index(body, `[Software\\Wine\\DllOverrides]`)
	end := strings.Index(body, `[Software\\Wine\\Fonts]`)
	if !strings.Contains(body[start:end], `"version"="native,builtin"`) {
		t.Errorf("the entry is not in the section:\n%s", body[start:end])
	}
	if got, ok := ReadDllOverride(prefix, DLLName, ""); !ok || got != DLLValue {
		t.Errorf("value = %q, %v", got, ok)
	}
}

func TestSetDllOverrideAddsAWineStyleHeaderWhenMissing(t *testing.T) {
	without := wineUserReg[:strings.Index(wineUserReg, `[Software\\Wine\\DllOverrides]`)] + "[Software\\\\Wine\\\\Fonts] 1793463286\n"
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), without)
	if _, ok := ReadDllOverride(prefix, DLLName, ""); ok {
		t.Fatal("the fixture should start without the section")
	}
	SetDllOverride(prefix, DLLName, DLLValue, "", "", nil)
	text, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(text), `[Software\\Wine\\DllOverrides]`) {
		t.Errorf("a WINE REGISTRY file needs the escaped header:\n%s", text)
	}
	if got, ok := ReadDllOverride(prefix, DLLName, ""); !ok || got != DLLValue {
		t.Errorf("value = %q, %v", got, ok)
	}
}

func TestSetDllOverrideCreatesUserRegWhenAbsent(t *testing.T) {
	prefix := prefixDir(t)
	if got := SetDllOverride(prefix, DLLName, DLLValue, "", "", nil); got != "registry" {
		t.Fatalf("via = %q", got)
	}
	if got, ok := ReadDllOverride(prefix, DLLName, ""); !ok || got != DLLValue {
		t.Errorf("value = %q, %v", got, ok)
	}
	text, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.HasPrefix(string(text), "REGEDIT4\n\n[Software\\Wine\\DllOverrides]\n") {
		t.Errorf("new file:\n%s", text)
	}
}

func TestSetDllOverrideWritesBackWithoutGrowth(t *testing.T) {
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), wineUserReg)
	SetDllOverride(prefix, DLLName, "native,builtin", "", "", nil)
	first, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	SetDllOverride(prefix, DLLName, "native,builtin", "", "", nil)
	second, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	if string(first) != string(second) {
		t.Errorf("a second write changed the file:\n%s\n---\n%s", first, second)
	}
}

func TestSetDllOverridePrefersTheWineBinary(t *testing.T) {
	prefix := prefixDir(t)
	type call struct {
		argv []string
		env  map[string]string
	}
	var calls []call
	runner := func(argv []string, env map[string]string) int {
		calls = append(calls, call{argv, env})
		return 0
	}
	wine := filepath.Join(t.TempDir(), "wine")
	if got := SetDllOverride(prefix, DLLName, DLLValue, "", wine, runner); got != "wine" {
		t.Fatalf("via = %q", got)
	}
	if len(calls) != 1 {
		t.Fatalf("calls = %d", len(calls))
	}
	argv := calls[0].argv
	if argv[0] != wine || argv[1] != "reg" || argv[2] != "add" {
		t.Errorf("argv = %v", argv)
	}
	if !strings.Contains(strings.Join(argv, " "), `HKCU\Software\Wine\DllOverrides`) {
		t.Errorf("the key is missing from %v", argv)
	}
	if !containsToken(argv, DLLName) || !containsToken(argv, DLLValue) {
		t.Errorf("name and value should be arguments: %v", argv)
	}
	if calls[0].env["WINEPREFIX"] != filepath.ToSlash(prefix) || calls[0].env["WINEDEBUG"] != "-all" {
		t.Errorf("env = %v", calls[0].env)
	}
	if _, ok := ReadDllOverride(prefix, DLLName, ""); ok {
		t.Error("the wine path should not also edit the file")
	}
}

func TestSetDllOverrideFallsBackWhenWineFails(t *testing.T) {
	prefix := prefixDir(t)
	runner := func(argv []string, env map[string]string) int { return 1 }
	if got := SetDllOverride(prefix, DLLName, DLLValue, "", filepath.Join(t.TempDir(), "wine"), runner); got != "registry" {
		t.Fatalf("via = %q", got)
	}
	if got, ok := ReadDllOverride(prefix, DLLName, ""); !ok || got != DLLValue {
		t.Errorf("value = %q, %v", got, ok)
	}
}

func TestClearDllOverrideRemovesOnlyThatEntry(t *testing.T) {
	prefix := prefixDir(t)
	write(t, filepath.Join(prefix, "user.reg"), wineUserReg)
	if got := ClearDllOverride(prefix, DLLName, "", "", nil); got != "registry" {
		t.Fatalf("via = %q", got)
	}
	if _, ok := ReadDllOverride(prefix, DLLName, ""); ok {
		t.Error("the entry should be gone")
	}
	text, err := os.ReadFile(filepath.Join(prefix, "user.reg"))
	if err != nil {
		t.Fatal(err)
	}
	body := string(text)
	if !strings.Contains(body, `"api-ms-win-crt-heap-l1-1-0"="native,builtin"`) {
		t.Errorf("a sibling entry was lost:\n%s", body)
	}
	if !strings.Contains(body, `[Software\\Wine\\DllOverrides]`) {
		t.Errorf("the section header should stay:\n%s", body)
	}

	runner := func(argv []string, env map[string]string) int { return 0 }
	via := ClearDllOverride(prefix, DLLName, "", filepath.Join(t.TempDir(), "wine"), runner)
	if via != "wine" {
		t.Errorf("via = %q", via)
	}
}

func TestProtonRootsListsInstalledAndUserTools(t *testing.T) {
	library := filepath.Join(t.TempDir(), "lib")
	for _, name := range []string{
		"steamapps/common/Proton 10.0",
		"steamapps/common/Proton 9.0 (Beta)",
		"steamapps/common/SteamLinuxRuntime",
		"compatibilitytools.d/Proton-GE",
	} {
		if err := os.MkdirAll(filepath.Join(library, name), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	var names []string
	for _, tool := range ProtonRoots(library) {
		names = append(names, filepath.Base(tool))
	}
	want := []string{"Proton 10.0", "Proton 9.0 (Beta)", "Proton-GE"}
	if !reflect.DeepEqual(names, want) {
		t.Errorf("ProtonRoots = %v, want %v", names, want)
	}
}

func TestPickProton(t *testing.T) {
	library := filepath.Join(t.TempDir(), "lib")
	for _, name := range []string{
		"steamapps/common/Proton 9.0",
		"steamapps/common/Proton 10.0",
	} {
		if err := os.MkdirAll(filepath.Join(library, name), 0o755); err != nil {
			t.Fatal(err)
		}
	}
	if got := filepath.Base(PickProton(library, "")); got != "Proton 10.0" {
		t.Errorf("highest numbered = %q", got)
	}
	if err := os.MkdirAll(filepath.Join(library, "compatibilitytools.d", "Proton-GE-10-2"), 0o755); err != nil {
		t.Fatal(err)
	}
	if got := filepath.Base(PickProton(library, "")); got != "Proton-GE-10-2" {
		t.Errorf("the numbers decide, so 10.2 beats 10.0: %q", got)
	}
	if got := filepath.Base(PickProton(library, "proton_ge_10")); got != "Proton-GE-10-2" {
		t.Errorf("forced = %q", got)
	}
	if got := PickProton(library, "proton_experimental_9"); got != "" {
		t.Errorf("a forced name with no match should be empty, got %q", got)
	}
	if got := PickProton(library, "   "); got != "" {
		t.Errorf("a blank forced name should be empty, got %q", got)
	}

	empty := filepath.Join(t.TempDir(), "lib")
	if err := os.MkdirAll(filepath.Join(empty, "steamapps", "common"), 0o755); err != nil {
		t.Fatal(err)
	}
	if got := PickProton(empty, ""); got != "" {
		t.Errorf("no tools = %q", got)
	}
}

func TestProtonWineBin(t *testing.T) {
	tool := filepath.Join(t.TempDir(), "Proton 10.0")
	if err := os.MkdirAll(filepath.Join(tool, "files", "bin"), 0o755); err != nil {
		t.Fatal(err)
	}
	if got := ProtonWineBin(tool); got != "" {
		t.Errorf("no binary = %q", got)
	}
	write(t, filepath.Join(tool, "files", "bin", "wine"), "#!/bin/sh\n")
	if got := filepath.Base(ProtonWineBin(tool)); got != "wine" {
		t.Errorf("wine = %q", got)
	}
	write(t, filepath.Join(tool, "files", "bin", "wine64"), "#!/bin/sh\n")
	if got := filepath.Base(ProtonWineBin(tool)); got != "wine64" {
		t.Errorf("wine64 should win: %q", got)
	}
}

func TestLaunchOption(t *testing.T) {
	got := LaunchOption("/media/sdcard/Megabonk/dotnet6-win")
	want := `DOTNET_ROOT=Z:\media\sdcard\Megabonk\dotnet6-win %command%`
	if got != want {
		t.Errorf("LaunchOption = %q, want %q", got, want)
	}
	if got := LaunchOption("/g/dotnet6-win", "LD_PRELOAD=x.so"); got != `DOTNET_ROOT=Z:\g\dotnet6-win LD_PRELOAD=x.so %command%` {
		t.Errorf("with extra assignments = %q", got)
	}
}

func TestUsablePrefixAndRemoveRuntime(t *testing.T) {
	prefix := prefixDir(t)
	if !UsablePrefix(prefix) {
		t.Error("a prefix with drive_c is usable")
	}
	if UsablePrefix(filepath.Join(t.TempDir(), "nope")) {
		t.Error("a missing prefix is not usable")
	}

	target := RuntimeTarget(prefix)
	if err := os.MkdirAll(target, 0o755); err != nil {
		t.Fatal(err)
	}
	if !RemoveRuntime(target) {
		t.Error("an existing runtime should report removal")
	}
	if RemoveRuntime(target) {
		t.Error("removing nothing should report false")
	}
}

func TestRunReportsAFailureForAMissingBinary(t *testing.T) {
	if got := run([]string{filepath.Join(t.TempDir(), "no-such-wine"), "reg"}, map[string]string{}); got != 1 {
		t.Errorf("run = %d, want 1", got)
	}
	if got := run(nil, nil); got != 1 {
		t.Errorf("run(nil) = %d, want 1", got)
	}
}
